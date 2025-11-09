"""
Divergence Detection System
Implements Tier-1 simplified divergence rules for RORO trading
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np
from loguru import logger

from ..data_feeds.base import MarketData
from ..utils.config import ConfigManager


class DivergenceType(Enum):
    """Types of divergence"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NONE = "NONE"


@dataclass
class DivergenceSignal:
    """Divergence signal container"""
    type: DivergenceType
    confidence: float  # 0-1 scale
    timestamp: datetime
    us500_level: float
    usdjpy_level: float
    vix_level: float
    volume_declining: bool
    persistence_minutes: int
    expected_reversal_time: int  # minutes

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'type': self.type.value,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'us500_level': self.us500_level,
            'usdjpy_level': self.usdjpy_level,
            'vix_level': self.vix_level,
            'volume_declining': self.volume_declining,
            'persistence_minutes': self.persistence_minutes,
            'expected_reversal_time': self.expected_reversal_time
        }


class DivergenceDetector:
    """Tier-1 divergence detection engine"""

    def __init__(self, config: ConfigManager):
        """
        Initialize divergence detector

        Args:
            config: Configuration manager
        """
        self.config = config
        self.divergence_config = config.get('divergence', {})

        # Detection parameters
        self.lookback_period = self.divergence_config.get('lookback_period', 1800)  # 30 mins
        self.min_persistence = self.divergence_config.get('min_persistence', 600)  # 10 mins

        # Price history (for tracking highs/lows)
        self.price_history: Dict[str, deque] = {
            'US500': deque(maxlen=self.lookback_period),
            'USDJPY': deque(maxlen=self.lookback_period),
            'VIX': deque(maxlen=self.lookback_period),
            'DXY': deque(maxlen=self.lookback_period)
        }

        # Volume history
        self.volume_history: Dict[str, deque] = {
            'US500': deque(maxlen=self.lookback_period),
            'USDJPY': deque(maxlen=self.lookback_period)
        }

        # Divergence tracking
        self.current_divergence: Optional[DivergenceSignal] = None
        self.divergence_start_time: Optional[datetime] = None

        # Failed signal tracking
        self.consecutive_failures = 0
        self.max_failures = self.divergence_config.get('max_consecutive_failures', 3)
        self.suspended_until: Optional[datetime] = None

    def update_market_data(self, market_data_dict: Dict[str, MarketData]) -> None:
        """
        Update price and volume history

        Args:
            market_data_dict: Dictionary of instrument -> MarketData
        """
        timestamp = datetime.now()

        for instrument, data in market_data_dict.items():
            if instrument in self.price_history:
                self.price_history[instrument].append((timestamp, data.close))

            if instrument in self.volume_history:
                self.volume_history[instrument].append((timestamp, data.volume))

    def find_recent_extreme(
        self,
        instrument: str,
        extreme_type: str,
        lookback_minutes: int = 30
    ) -> Optional[Tuple[datetime, float]]:
        """
        Find recent high or low

        Args:
            instrument: Instrument name
            extreme_type: 'high' or 'low'
            lookback_minutes: Lookback period

        Returns:
            Tuple of (timestamp, price) or None
        """
        if instrument not in self.price_history or not self.price_history[instrument]:
            return None

        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        recent = [(ts, price) for ts, price in self.price_history[instrument] if ts > cutoff]

        if not recent:
            return None

        if extreme_type == 'high':
            return max(recent, key=lambda x: x[1])
        elif extreme_type == 'low':
            return min(recent, key=lambda x: x[1])

        return None

    def is_volume_declining(self, instrument: str, lookback_minutes: int = 10) -> bool:
        """
        Check if volume is declining

        Args:
            instrument: Instrument name
            lookback_minutes: Lookback period

        Returns:
            True if volume declining
        """
        if instrument not in self.volume_history or len(self.volume_history[instrument]) < 2:
            return False

        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        recent = [vol for ts, vol in self.volume_history[instrument] if ts > cutoff]

        if len(recent) < 2:
            return False

        # Simple check: recent volume < earlier volume
        recent_avg = np.mean(recent[-3:]) if len(recent) >= 3 else recent[-1]
        earlier_avg = np.mean(recent[:3]) if len(recent) >= 3 else recent[0]

        return recent_avg < earlier_avg * 0.9  # 10% decline

    def check_vix_condition(
        self,
        vix_data: MarketData,
        condition: str
    ) -> bool:
        """
        Check VIX condition for divergence

        Args:
            vix_data: VIX market data
            condition: 'declining_or_flat' for bullish, 'rising' for bearish

        Returns:
            True if condition met
        """
        if 'VIX' not in self.price_history or len(self.price_history['VIX']) < 2:
            return False

        # Get recent VIX movement
        recent_vix = list(self.price_history['VIX'])[-5:]  # Last 5 data points

        if len(recent_vix) < 2:
            return False

        vix_change = (recent_vix[-1][1] - recent_vix[0][1]) / recent_vix[0][1]

        if condition == 'declining_or_flat':
            return vix_change <= 0.01  # Flat or declining
        elif condition == 'rising':
            return vix_change > 0.01

        return False

    def detect_bullish_divergence(
        self,
        market_data_dict: Dict[str, MarketData]
    ) -> Optional[DivergenceSignal]:
        """
        Detect bullish divergence using Tier-1 rules

        Rules:
        1. SPX makes new intraday low
        2. USDJPY fails to make new low (higher low)
        3. VIX declining or flat during selloff
        4. Volume declining on SPX down-move
        5. Persists for 2+ candles (10 mins)

        Args:
            market_data_dict: Market data dictionary

        Returns:
            DivergenceSignal or None
        """
        if 'US500' not in market_data_dict or 'USDJPY' not in market_data_dict:
            return None

        us500_data = market_data_dict['US500']
        usdjpy_data = market_data_dict['USDJPY']
        vix_data = market_data_dict.get('VIX')

        # Rule 1: SPX makes new intraday low
        spx_low = self.find_recent_extreme('US500', 'low', 30)
        if spx_low is None:
            return None

        is_new_low = us500_data.close <= spx_low[1] * 1.001  # Within 0.1%

        if not is_new_low:
            return None

        # Rule 2: USDJPY fails to make new low (higher low)
        usdjpy_low = self.find_recent_extreme('USDJPY', 'low', 30)
        if usdjpy_low is None:
            return None

        usdjpy_higher_low = usdjpy_data.close > usdjpy_low[1] * 1.001

        if not usdjpy_higher_low:
            return None

        # Rule 3: VIX declining or flat
        vix_ok = True
        if vix_data:
            vix_ok = self.check_vix_condition(vix_data, 'declining_or_flat')

        # Rule 4: Volume declining
        volume_declining = self.is_volume_declining('US500', 10)

        # Calculate confidence
        confidence = 0.5  # Base confidence

        if usdjpy_higher_low:
            confidence += 0.2
        if vix_ok:
            confidence += 0.2
        if volume_declining:
            confidence += 0.1

        confidence = min(confidence, 1.0)

        # Check if meets minimum confidence threshold
        min_confidence = self.divergence_config.get('bullish', {}).get('confidence_threshold', 0.6)

        if confidence < min_confidence:
            return None

        # Check persistence
        if self.current_divergence and self.current_divergence.type == DivergenceType.BULLISH:
            persistence = (datetime.now() - self.divergence_start_time).total_seconds()
        else:
            persistence = 0
            self.divergence_start_time = datetime.now()

        # Must persist for min duration
        if persistence < self.min_persistence:
            logger.debug(f"Bullish divergence detected but not persistent yet: {persistence}s")
            # Don't return signal yet, but track it
            self.current_divergence = DivergenceSignal(
                type=DivergenceType.BULLISH,
                confidence=confidence,
                timestamp=datetime.now(),
                us500_level=us500_data.close,
                usdjpy_level=usdjpy_data.close,
                vix_level=vix_data.close if vix_data else 0,
                volume_declining=volume_declining,
                persistence_minutes=int(persistence / 60),
                expected_reversal_time=45  # 30-60 minutes
            )
            return None

        # Persistent divergence - return signal
        signal = DivergenceSignal(
            type=DivergenceType.BULLISH,
            confidence=confidence,
            timestamp=datetime.now(),
            us500_level=us500_data.close,
            usdjpy_level=usdjpy_data.close,
            vix_level=vix_data.close if vix_data else 0,
            volume_declining=volume_declining,
            persistence_minutes=int(persistence / 60),
            expected_reversal_time=45
        )

        logger.info(f"BULLISH DIVERGENCE DETECTED - Confidence: {confidence:.2f}")

        return signal

    def detect_bearish_divergence(
        self,
        market_data_dict: Dict[str, MarketData]
    ) -> Optional[DivergenceSignal]:
        """
        Detect bearish divergence using Tier-1 rules

        Rules:
        1. SPX makes new intraday high
        2. USDJPY fails to make new high (lower high)
        3. DXY strengthening despite risk-on appearance
        4. Volume declining on SPX rally
        5. Persists for 2+ candles (10 mins)

        Args:
            market_data_dict: Market data dictionary

        Returns:
            DivergenceSignal or None
        """
        if 'US500' not in market_data_dict or 'USDJPY' not in market_data_dict:
            return None

        us500_data = market_data_dict['US500']
        usdjpy_data = market_data_dict['USDJPY']
        dxy_data = market_data_dict.get('DXY')

        # Rule 1: SPX makes new intraday high
        spx_high = self.find_recent_extreme('US500', 'high', 30)
        if spx_high is None:
            return None

        is_new_high = us500_data.close >= spx_high[1] * 0.999

        if not is_new_high:
            return None

        # Rule 2: USDJPY fails to make new high (lower high)
        usdjpy_high = self.find_recent_extreme('USDJPY', 'high', 30)
        if usdjpy_high is None:
            return None

        usdjpy_lower_high = usdjpy_data.close < usdjpy_high[1] * 0.999

        if not usdjpy_lower_high:
            return None

        # Rule 3: DXY strengthening
        dxy_strengthening = False
        if dxy_data and 'DXY' in self.price_history and len(self.price_history['DXY']) >= 2:
            recent_dxy = list(self.price_history['DXY'])[-5:]
            if len(recent_dxy) >= 2:
                dxy_change = (recent_dxy[-1][1] - recent_dxy[0][1]) / recent_dxy[0][1]
                dxy_strengthening = dxy_change > 0.001  # 0.1% increase

        # Rule 4: Volume declining
        volume_declining = self.is_volume_declining('US500', 10)

        # Calculate confidence
        confidence = 0.5

        if usdjpy_lower_high:
            confidence += 0.2
        if dxy_strengthening:
            confidence += 0.2
        if volume_declining:
            confidence += 0.1

        confidence = min(confidence, 1.0)

        # Check threshold
        min_confidence = self.divergence_config.get('bearish', {}).get('confidence_threshold', 0.6)

        if confidence < min_confidence:
            return None

        # Check persistence
        if self.current_divergence and self.current_divergence.type == DivergenceType.BEARISH:
            persistence = (datetime.now() - self.divergence_start_time).total_seconds()
        else:
            persistence = 0
            self.divergence_start_time = datetime.now()

        if persistence < self.min_persistence:
            logger.debug(f"Bearish divergence detected but not persistent yet: {persistence}s")
            self.current_divergence = DivergenceSignal(
                type=DivergenceType.BEARISH,
                confidence=confidence,
                timestamp=datetime.now(),
                us500_level=us500_data.close,
                usdjpy_level=usdjpy_data.close,
                vix_level=market_data_dict.get('VIX').close if 'VIX' in market_data_dict else 0,
                volume_declining=volume_declining,
                persistence_minutes=int(persistence / 60),
                expected_reversal_time=45
            )
            return None

        signal = DivergenceSignal(
            type=DivergenceType.BEARISH,
            confidence=confidence,
            timestamp=datetime.now(),
            us500_level=us500_data.close,
            usdjpy_level=usdjpy_data.close,
            vix_level=market_data_dict.get('VIX').close if 'VIX' in market_data_dict else 0,
            volume_declining=volume_declining,
            persistence_minutes=int(persistence / 60),
            expected_reversal_time=45
        )

        logger.info(f"BEARISH DIVERGENCE DETECTED - Confidence: {confidence:.2f}")

        return signal

    def detect_divergence(
        self,
        market_data_dict: Dict[str, MarketData]
    ) -> Optional[DivergenceSignal]:
        """
        Detect any divergence (bullish or bearish)

        Args:
            market_data_dict: Market data dictionary

        Returns:
            DivergenceSignal or None
        """
        # Check if suspended
        if self.suspended_until and datetime.now() < self.suspended_until:
            logger.debug("Divergence detection suspended due to consecutive failures")
            return None

        # Update data
        self.update_market_data(market_data_dict)

        # Check for bullish divergence first
        bullish = self.detect_bullish_divergence(market_data_dict)
        if bullish:
            return bullish

        # Check for bearish divergence
        bearish = self.detect_bearish_divergence(market_data_dict)
        if bearish:
            return bearish

        # Reset current divergence if no signal
        if self.current_divergence:
            self.current_divergence = None
            self.divergence_start_time = None

        return None

    def record_signal_failure(self) -> None:
        """Record a failed divergence signal"""
        self.consecutive_failures += 1

        logger.warning(
            f"Divergence signal failed. Consecutive failures: {self.consecutive_failures}"
        )

        if self.consecutive_failures >= self.max_failures:
            # Suspend divergence trading
            suspension_duration = self.divergence_config.get('suspension_duration', 3600)
            self.suspended_until = datetime.now() + timedelta(seconds=suspension_duration)

            logger.error(
                f"Divergence detection suspended until {self.suspended_until} "
                f"due to {self.consecutive_failures} consecutive failures"
            )

    def record_signal_success(self) -> None:
        """Record a successful divergence signal"""
        self.consecutive_failures = 0
        logger.info("Divergence signal successful - failure count reset")

    def is_suspended(self) -> bool:
        """Check if divergence detection is suspended"""
        if self.suspended_until and datetime.now() < self.suspended_until:
            return True
        return False

    def get_status(self) -> Dict:
        """
        Get current divergence detector status

        Returns:
            Status dictionary
        """
        return {
            'suspended': self.is_suspended(),
            'suspended_until': self.suspended_until.isoformat() if self.suspended_until else None,
            'consecutive_failures': self.consecutive_failures,
            'current_divergence': self.current_divergence.to_dict() if self.current_divergence else None,
            'sample_sizes': {
                inst: len(hist) for inst, hist in self.price_history.items()
            }
        }
