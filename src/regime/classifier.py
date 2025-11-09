"""
Market Regime Classification Engine
Implements VIX-adaptive threshold system for RORO regime detection
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger
import numpy as np

from ..data_feeds.base import MarketData
from ..utils.config import ConfigManager


class RegimeType(Enum):
    """Market regime types"""
    STRONG_RISK_ON = "STRONG_RISK_ON"
    WEAK_RISK_ON = "WEAK_RISK_ON"
    TRANSITION = "TRANSITION"
    WEAK_RISK_OFF = "WEAK_RISK_OFF"
    STRONG_RISK_OFF = "STRONG_RISK_OFF"


@dataclass
class RegimeSignal:
    """Individual regime signal from instrument"""
    instrument: str
    signal_type: str  # 'bullish', 'bearish', 'neutral'
    strength: float  # 0-1 scale
    value: float
    threshold: float
    timestamp: datetime
    sustained_duration: int  # seconds


@dataclass
class RegimeClassification:
    """Complete regime classification result"""
    regime_type: RegimeType
    confidence: float  # 0-1 scale
    signals: List[RegimeSignal]
    timestamp: datetime
    vix_level: float
    vix_multiplier: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'regime_type': self.regime_type.value,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'vix_level': self.vix_level,
            'vix_multiplier': self.vix_multiplier,
            'signals': [
                {
                    'instrument': s.instrument,
                    'signal_type': s.signal_type,
                    'strength': s.strength,
                    'value': s.value,
                    'threshold': s.threshold
                }
                for s in self.signals
            ]
        }


class RegimeClassifier:
    """VIX-adaptive market regime classifier"""

    def __init__(self, config: ConfigManager):
        """
        Initialize regime classifier

        Args:
            config: Configuration manager
        """
        self.config = config
        self.regime_config = config.get('regime', {})

        # Historical data for time confirmation
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {
            'US500': [],
            'USDJPY': [],
            'VIX': [],
            'US10Y': [],
            'DXY': []
        }

        # Current regime state
        self.current_regime: Optional[RegimeClassification] = None
        self.regime_start_time: Optional[datetime] = None

    def update_price_history(self, instrument: str, price: float, timestamp: datetime) -> None:
        """
        Update price history for time confirmation

        Args:
            instrument: Instrument name
            price: Current price
            timestamp: Timestamp
        """
        if instrument not in self.price_history:
            self.price_history[instrument] = []

        self.price_history[instrument].append((timestamp, price))

        # Keep only last 30 minutes
        cutoff = timestamp - timedelta(minutes=30)
        self.price_history[instrument] = [
            (ts, p) for ts, p in self.price_history[instrument]
            if ts > cutoff
        ]

    def get_vix_thresholds(self, vix_level: float) -> Dict:
        """
        Get VIX-adaptive thresholds

        Args:
            vix_level: Current VIX value

        Returns:
            Threshold configuration
        """
        return self.config.get_vix_threshold_config(vix_level)

    def calculate_move_percentage(
        self,
        instrument: str,
        current_price: float,
        lookback_minutes: int = 5
    ) -> Optional[float]:
        """
        Calculate percentage move over lookback period

        Args:
            instrument: Instrument name
            current_price: Current price
            lookback_minutes: Lookback period in minutes

        Returns:
            Percentage move or None
        """
        if instrument not in self.price_history or not self.price_history[instrument]:
            return None

        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        historical = [
            (ts, p) for ts, p in self.price_history[instrument]
            if ts > cutoff
        ]

        if not historical:
            return None

        # Get price from lookback period
        start_price = historical[0][1]

        if start_price == 0:
            return None

        return (current_price - start_price) / start_price

    def check_time_confirmation(
        self,
        instrument: str,
        direction: str,
        required_duration: int
    ) -> bool:
        """
        Check if move has been sustained for required duration

        Args:
            instrument: Instrument name
            direction: 'up' or 'down'
            required_duration: Required duration in seconds

        Returns:
            True if move sustained
        """
        if instrument not in self.price_history or len(self.price_history[instrument]) < 2:
            return False

        # Get prices over required duration
        cutoff = datetime.now() - timedelta(seconds=required_duration)
        historical = [
            (ts, p) for ts, p in self.price_history[instrument]
            if ts > cutoff
        ]

        if len(historical) < 2:
            return False

        prices = [p for _, p in historical]

        if direction == 'up':
            # Check if generally trending up
            return prices[-1] > prices[0] and min(prices) >= prices[0] * 0.995
        elif direction == 'down':
            # Check if generally trending down
            return prices[-1] < prices[0] and max(prices) <= prices[0] * 1.005
        else:
            return False

    def analyze_us500_signal(
        self,
        market_data: MarketData,
        vix_thresholds: Dict
    ) -> RegimeSignal:
        """
        Analyze US500 (S&P 500) for regime signal

        Args:
            market_data: Current market data
            vix_thresholds: VIX-adaptive thresholds

        Returns:
            RegimeSignal
        """
        strong_threshold = vix_thresholds.get('strong_move', 0.005)
        weak_threshold = vix_thresholds.get('weak_move', 0.001)
        time_confirm = vix_thresholds.get('time_confirm', 300)

        # Calculate move
        move_pct = self.calculate_move_percentage('US500', market_data.close, 5)

        if move_pct is None:
            return RegimeSignal(
                instrument='US500',
                signal_type='neutral',
                strength=0.0,
                value=0.0,
                threshold=strong_threshold,
                timestamp=datetime.now(),
                sustained_duration=0
            )

        # Determine signal type and strength
        if move_pct > strong_threshold:
            # Check time confirmation
            if self.check_time_confirmation('US500', 'up', time_confirm):
                signal_type = 'bullish'
                strength = min(abs(move_pct) / strong_threshold, 1.0)
            else:
                signal_type = 'neutral'
                strength = 0.5
        elif move_pct < -strong_threshold:
            if self.check_time_confirmation('US500', 'down', time_confirm):
                signal_type = 'bearish'
                strength = min(abs(move_pct) / strong_threshold, 1.0)
            else:
                signal_type = 'neutral'
                strength = 0.5
        elif weak_threshold < abs(move_pct) < strong_threshold:
            signal_type = 'bullish' if move_pct > 0 else 'bearish'
            strength = abs(move_pct) / strong_threshold * 0.6
        else:
            signal_type = 'neutral'
            strength = abs(move_pct) / weak_threshold * 0.3

        # Check VWAP position for additional confirmation
        above_vwap = market_data.close > market_data.vwap if market_data.vwap else True
        if signal_type == 'bullish' and not above_vwap:
            strength *= 0.8
        elif signal_type == 'bearish' and above_vwap:
            strength *= 0.8

        return RegimeSignal(
            instrument='US500',
            signal_type=signal_type,
            strength=strength,
            value=move_pct,
            threshold=strong_threshold,
            timestamp=datetime.now(),
            sustained_duration=time_confirm if strength > 0.7 else 0
        )

    def analyze_usdjpy_signal(
        self,
        market_data: MarketData,
        vix_thresholds: Dict
    ) -> RegimeSignal:
        """
        Analyze USDJPY for regime signal

        Args:
            market_data: Current market data
            vix_thresholds: VIX-adaptive thresholds

        Returns:
            RegimeSignal
        """
        strong_threshold = vix_thresholds.get('strong_move', 0.005)
        time_confirm = vix_thresholds.get('time_confirm', 300)

        move_pct = self.calculate_move_percentage('USDJPY', market_data.close, 5)

        if move_pct is None:
            return RegimeSignal(
                instrument='USDJPY',
                signal_type='neutral',
                strength=0.0,
                value=0.0,
                threshold=strong_threshold,
                timestamp=datetime.now(),
                sustained_duration=0
            )

        # USDJPY interpretation: up = risk-on, down = risk-off
        if move_pct > strong_threshold:
            if self.check_time_confirmation('USDJPY', 'up', time_confirm):
                signal_type = 'bullish'
                strength = min(abs(move_pct) / strong_threshold, 1.0)
            else:
                signal_type = 'neutral'
                strength = 0.5
        elif move_pct < -strong_threshold:
            if self.check_time_confirmation('USDJPY', 'down', time_confirm):
                signal_type = 'bearish'
                strength = min(abs(move_pct) / strong_threshold, 1.0)
            else:
                signal_type = 'neutral'
                strength = 0.5
        else:
            signal_type = 'neutral'
            strength = abs(move_pct) / strong_threshold * 0.5

        return RegimeSignal(
            instrument='USDJPY',
            signal_type=signal_type,
            strength=strength,
            value=move_pct,
            threshold=strong_threshold,
            timestamp=datetime.now(),
            sustained_duration=time_confirm if strength > 0.7 else 0
        )

    def analyze_vix_signal(self, market_data: MarketData) -> RegimeSignal:
        """
        Analyze VIX for regime signal

        Args:
            market_data: Current VIX data

        Returns:
            RegimeSignal
        """
        # VIX change threshold (not adaptive)
        vix_threshold = 0.05  # 5% change

        move_pct = self.calculate_move_percentage('VIX', market_data.close, 5)

        if move_pct is None:
            return RegimeSignal(
                instrument='VIX',
                signal_type='neutral',
                strength=0.0,
                value=market_data.close,
                threshold=vix_threshold,
                timestamp=datetime.now(),
                sustained_duration=0
            )

        # VIX interpretation: down = risk-on, up = risk-off
        if move_pct < -vix_threshold:
            signal_type = 'bullish'  # VIX falling = risk-on
            strength = min(abs(move_pct) / vix_threshold, 1.0)
        elif move_pct > vix_threshold:
            signal_type = 'bearish'  # VIX rising = risk-off
            strength = min(abs(move_pct) / vix_threshold, 1.0)
        else:
            signal_type = 'neutral'
            strength = abs(move_pct) / vix_threshold * 0.5

        return RegimeSignal(
            instrument='VIX',
            signal_type=signal_type,
            strength=strength,
            value=move_pct,
            threshold=vix_threshold,
            timestamp=datetime.now(),
            sustained_duration=0
        )

    def classify_regime(
        self,
        market_data_dict: Dict[str, MarketData]
    ) -> RegimeClassification:
        """
        Classify current market regime

        Args:
            market_data_dict: Dictionary of instrument -> MarketData

        Returns:
            RegimeClassification
        """
        # Update price history
        for instrument, data in market_data_dict.items():
            self.update_price_history(instrument, data.close, data.timestamp)

        # Get VIX level and thresholds
        vix_data = market_data_dict.get('VIX')
        if vix_data is None:
            logger.warning("VIX data not available for regime classification")
            vix_level = 20.0  # Default
        else:
            vix_level = vix_data.close

        vix_thresholds = self.get_vix_thresholds(vix_level)

        # Analyze all signals
        signals = []

        if 'US500' in market_data_dict:
            signals.append(self.analyze_us500_signal(market_data_dict['US500'], vix_thresholds))

        if 'USDJPY' in market_data_dict:
            signals.append(self.analyze_usdjpy_signal(market_data_dict['USDJPY'], vix_thresholds))

        if 'VIX' in market_data_dict:
            signals.append(self.analyze_vix_signal(market_data_dict['VIX']))

        # Count bullish/bearish signals
        strong_bullish = sum(1 for s in signals if s.signal_type == 'bullish' and s.strength > 0.7)
        strong_bearish = sum(1 for s in signals if s.signal_type == 'bearish' and s.strength > 0.7)
        weak_bullish = sum(1 for s in signals if s.signal_type == 'bullish' and 0.4 < s.strength <= 0.7)
        weak_bearish = sum(1 for s in signals if s.signal_type == 'bearish' and 0.4 < s.strength <= 0.7)

        # Classify regime
        required_signals = self.regime_config.get('strong_risk_on', {}).get('required_signals', 3)

        if strong_bullish >= required_signals:
            regime_type = RegimeType.STRONG_RISK_ON
            confidence = min(strong_bullish / len(signals), 1.0)
        elif strong_bearish >= required_signals:
            regime_type = RegimeType.STRONG_RISK_OFF
            confidence = min(strong_bearish / len(signals), 1.0)
        elif weak_bullish >= 2 or (weak_bullish >= 1 and strong_bullish >= 1):
            regime_type = RegimeType.WEAK_RISK_ON
            confidence = 0.6
        elif weak_bearish >= 2 or (weak_bearish >= 1 and strong_bearish >= 1):
            regime_type = RegimeType.WEAK_RISK_OFF
            confidence = 0.6
        else:
            regime_type = RegimeType.TRANSITION
            confidence = 0.3

        classification = RegimeClassification(
            regime_type=regime_type,
            confidence=confidence,
            signals=signals,
            timestamp=datetime.now(),
            vix_level=vix_level,
            vix_multiplier=vix_thresholds.get('multiplier', 1.0)
        )

        # Update current regime
        if self.current_regime is None or self.current_regime.regime_type != regime_type:
            self.regime_start_time = datetime.now()
            logger.info(f"Regime change detected: {regime_type.value} (confidence: {confidence:.2f})")

        self.current_regime = classification

        return classification

    def get_regime_trading_bias(self) -> Dict[str, Any]:
        """
        Get trading bias for current regime

        Returns:
            Trading bias dictionary
        """
        if self.current_regime is None:
            return {'action': 'NO_TRADE', 'reason': 'No regime classified'}

        regime = self.current_regime.regime_type

        if regime == RegimeType.STRONG_RISK_ON:
            return {
                'action': 'LONG',
                'primary_instruments': ['US500', 'NASDAQ', 'DAX'],
                'secondary_instruments': ['AUDJPY', 'NZDJPY'],
                'avoid': ['Gold', 'Individual_Stocks'],
                'size_multiplier': 1.0,
                'confidence': self.current_regime.confidence
            }
        elif regime == RegimeType.WEAK_RISK_ON:
            return {
                'action': 'LONG',
                'primary_instruments': ['SPY', 'QQQ'],
                'size_multiplier': 0.5,
                'stops': 'tighter',
                'confidence': self.current_regime.confidence
            }
        elif regime == RegimeType.TRANSITION:
            return {
                'action': 'NO_NEW_POSITIONS',
                'existing_positions': 'reduce_to_25%',
                'reason': 'Conflicting signals',
                'confidence': self.current_regime.confidence
            }
        elif regime == RegimeType.WEAK_RISK_OFF:
            return {
                'action': 'SHORT',
                'primary_instruments': ['Russell_2000'],
                'secondary_instruments': ['Gold_LONG'],
                'size_multiplier': 0.5,
                'confidence': self.current_regime.confidence
            }
        elif regime == RegimeType.STRONG_RISK_OFF:
            return {
                'action': 'SHORT',
                'primary_instruments': ['DAX', 'FTSE'],
                'secondary_instruments': ['Gold_LONG', 'CHFJPY'],
                'avoid': ['Risk_currencies', 'Tech_stocks'],
                'size_multiplier': 1.0,
                'confidence': self.current_regime.confidence
            }

        return {'action': 'NO_TRADE'}
