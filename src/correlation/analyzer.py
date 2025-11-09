"""
Real-Time Correlation Analysis Module
Monitors correlation health across primary instruments
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from loguru import logger
from collections import deque

from ..data_feeds.base import MarketData
from ..utils.config import ConfigManager


class CorrelationHealth(Enum):
    """Correlation health status"""
    HEALTHY = "HEALTHY"  # > 0.7
    DEGRADED = "DEGRADED"  # 0.4 - 0.7
    BROKEN = "BROKEN"  # < 0.4


@dataclass
class CorrelationResult:
    """Correlation analysis result"""
    coefficient: float
    health: CorrelationHealth
    instrument_pair: Tuple[str, str]
    timestamp: datetime
    sample_size: int
    p_value: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'coefficient': self.coefficient,
            'health': self.health.value,
            'instrument_pair': self.instrument_pair,
            'timestamp': self.timestamp.isoformat(),
            'sample_size': self.sample_size,
            'p_value': self.p_value
        }


class CorrelationAnalyzer:
    """Real-time correlation analysis engine"""

    def __init__(self, config: ConfigManager):
        """
        Initialize correlation analyzer

        Args:
            config: Configuration manager
        """
        self.config = config
        self.correlation_config = config.get('correlation', {})

        # Window settings
        self.window_seconds = self.correlation_config.get('window', 1800)  # 30 minutes
        self.update_frequency = self.correlation_config.get('update_frequency', 60)

        # Health thresholds
        self.thresholds = self.correlation_config.get('health_thresholds', {
            'healthy': 0.7,
            'degraded': 0.4,
            'broken': 0.4
        })

        # Price history storage (rolling windows)
        self.price_history: Dict[str, deque] = {
            'US500': deque(maxlen=self.window_seconds),
            'USDJPY': deque(maxlen=self.window_seconds),
            'VIX': deque(maxlen=self.window_seconds),
            'US10Y': deque(maxlen=self.window_seconds),
            'DXY': deque(maxlen=self.window_seconds)
        }

        # Last update time
        self.last_update: Optional[datetime] = None

        # Current correlation matrix
        self.correlation_matrix: pd.DataFrame = pd.DataFrame()

        # Correlation health cache
        self.current_health: CorrelationHealth = CorrelationHealth.DEGRADED

    def update_prices(self, market_data_dict: Dict[str, MarketData]) -> None:
        """
        Update price history with new data

        Args:
            market_data_dict: Dictionary of instrument -> MarketData
        """
        timestamp = datetime.now()

        for instrument, data in market_data_dict.items():
            if instrument in self.price_history:
                # Store (timestamp, price) tuple
                self.price_history[instrument].append((timestamp, data.close))

        self.last_update = timestamp

    def calculate_correlation(
        self,
        instrument1: str,
        instrument2: str,
        min_samples: int = 30
    ) -> Optional[CorrelationResult]:
        """
        Calculate correlation between two instruments

        Args:
            instrument1: First instrument
            instrument2: Second instrument
            min_samples: Minimum number of samples required

        Returns:
            CorrelationResult or None
        """
        if instrument1 not in self.price_history or instrument2 not in self.price_history:
            logger.warning(f"Missing price history for {instrument1} or {instrument2}")
            return None

        hist1 = list(self.price_history[instrument1])
        hist2 = list(self.price_history[instrument2])

        if len(hist1) < min_samples or len(hist2) < min_samples:
            logger.debug(f"Insufficient samples for correlation: {len(hist1)}, {len(hist2)}")
            return None

        # Align timestamps and extract prices
        prices1 = []
        prices2 = []

        # Create DataFrames for alignment
        df1 = pd.DataFrame(hist1, columns=['timestamp', 'price'])
        df2 = pd.DataFrame(hist2, columns=['timestamp', 'price'])

        # Merge on timestamp (within 1 second tolerance)
        df1['timestamp'] = pd.to_datetime(df1['timestamp'])
        df2['timestamp'] = pd.to_datetime(df2['timestamp'])

        # Simple approach: resample to common frequency
        df1 = df1.set_index('timestamp').resample('1S').last().ffill()
        df2 = df2.set_index('timestamp').resample('1S').last().ffill()

        # Align indices
        common_index = df1.index.intersection(df2.index)

        if len(common_index) < min_samples:
            logger.debug(f"Insufficient aligned samples: {len(common_index)}")
            return None

        prices1 = df1.loc[common_index, 'price'].values
        prices2 = df2.loc[common_index, 'price'].values

        # Calculate returns
        returns1 = np.diff(prices1) / prices1[:-1]
        returns2 = np.diff(prices2) / prices2[:-1]

        # Handle NaN/Inf
        valid_mask = np.isfinite(returns1) & np.isfinite(returns2)
        returns1 = returns1[valid_mask]
        returns2 = returns2[valid_mask]

        if len(returns1) < min_samples:
            return None

        # Calculate Pearson correlation
        correlation = np.corrcoef(returns1, returns2)[0, 1]

        # Determine health
        if correlation >= self.thresholds['healthy']:
            health = CorrelationHealth.HEALTHY
        elif correlation >= self.thresholds['degraded']:
            health = CorrelationHealth.DEGRADED
        else:
            health = CorrelationHealth.BROKEN

        return CorrelationResult(
            coefficient=float(correlation),
            health=health,
            instrument_pair=(instrument1, instrument2),
            timestamp=datetime.now(),
            sample_size=len(returns1)
        )

    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        Calculate full correlation matrix for all instruments

        Returns:
            Correlation matrix DataFrame
        """
        instruments = list(self.price_history.keys())
        n = len(instruments)

        # Initialize matrix
        matrix = np.eye(n)

        for i, inst1 in enumerate(instruments):
            for j, inst2 in enumerate(instruments):
                if i < j:  # Only calculate upper triangle
                    result = self.calculate_correlation(inst1, inst2)
                    if result:
                        matrix[i, j] = result.coefficient
                        matrix[j, i] = result.coefficient

        # Create DataFrame
        self.correlation_matrix = pd.DataFrame(
            matrix,
            index=instruments,
            columns=instruments
        )

        return self.correlation_matrix

    def get_primary_correlation(self) -> Optional[CorrelationResult]:
        """
        Get correlation between primary instruments (US500 and USDJPY)

        Returns:
            CorrelationResult or None
        """
        return self.calculate_correlation('US500', 'USDJPY')

    def get_overall_health(self) -> CorrelationHealth:
        """
        Get overall correlation health across all instruments

        Returns:
            Overall CorrelationHealth status
        """
        # Calculate correlation matrix if needed
        if self.correlation_matrix.empty:
            self.calculate_correlation_matrix()

        if self.correlation_matrix.empty:
            return CorrelationHealth.BROKEN

        # Get primary correlation (US500 vs USDJPY)
        primary_result = self.get_primary_correlation()

        if primary_result is None:
            self.current_health = CorrelationHealth.BROKEN
            return self.current_health

        # Primary correlation drives overall health
        self.current_health = primary_result.health

        logger.debug(f"Correlation health: {self.current_health.value} ({primary_result.coefficient:.3f})")

        return self.current_health

    def get_position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on correlation health

        Returns:
            Multiplier (0.0 to 1.0)
        """
        health = self.get_overall_health()

        multipliers = self.correlation_config.get('position_size_multipliers', {
            'healthy': 1.0,
            'degraded': 0.5,
            'broken': 0.0
        })

        if health == CorrelationHealth.HEALTHY:
            return multipliers.get('healthy', 1.0)
        elif health == CorrelationHealth.DEGRADED:
            return multipliers.get('degraded', 0.5)
        else:
            return multipliers.get('broken', 0.0)

    def should_trade(self) -> Tuple[bool, str]:
        """
        Determine if trading should proceed based on correlation health

        Returns:
            Tuple of (should_trade, reason)
        """
        health = self.get_overall_health()

        if health == CorrelationHealth.HEALTHY:
            return (True, "Correlation healthy")
        elif health == CorrelationHealth.DEGRADED:
            return (True, "Correlation degraded - reduced size")
        else:
            return (False, "Correlation broken - no trading")

    def get_correlation_report(self) -> Dict:
        """
        Generate comprehensive correlation report

        Returns:
            Report dictionary
        """
        # Update correlation matrix
        matrix = self.calculate_correlation_matrix()
        primary = self.get_primary_correlation()
        health = self.get_overall_health()

        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': health.value,
            'position_size_multiplier': self.get_position_size_multiplier(),
            'primary_correlation': primary.to_dict() if primary else None,
            'correlation_matrix': matrix.to_dict() if not matrix.empty else {},
            'sample_sizes': {
                inst: len(hist) for inst, hist in self.price_history.items()
            }
        }

        return report

    def reset(self) -> None:
        """Reset all correlation data"""
        for inst in self.price_history:
            self.price_history[inst].clear()
        self.correlation_matrix = pd.DataFrame()
        self.current_health = CorrelationHealth.DEGRADED
        self.last_update = None
        logger.info("Correlation analyzer reset")

    def is_correlation_stable(self, lookback_periods: int = 3) -> bool:
        """
        Check if correlation has been stable over recent periods

        Args:
            lookback_periods: Number of periods to check

        Returns:
            True if stable
        """
        # This would require storing historical correlation values
        # For now, return True if current health is not BROKEN
        return self.current_health != CorrelationHealth.BROKEN
