"""
Base Data Feed Interface
Defines abstract interface for all data providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd


@dataclass
class MarketData:
    """Container for market data point"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    vwap: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask,
            'vwap': self.vwap
        }


class DataFeedBase(ABC):
    """Abstract base class for data feed providers"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data feed

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.is_connected = False
        self.subscriptions: List[str] = []

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to data provider

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data provider"""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time data for symbols

        Args:
            symbols: List of symbols to subscribe

        Returns:
            True if subscription successful
        """
        pass

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from symbols

        Args:
            symbols: List of symbols to unsubscribe

        Returns:
            True if unsubscribe successful
        """
        pass

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for symbol

        Args:
            symbol: Symbol to get price for

        Returns:
            Current price or None
        """
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get current market data snapshot

        Args:
            symbol: Symbol to get data for

        Returns:
            MarketData object or None
        """
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = '1m'
    ) -> pd.DataFrame:
        """
        Get historical data

        Args:
            symbol: Symbol to get data for
            start: Start datetime
            end: End datetime
            interval: Data interval (1m, 5m, 15m, 1h, 1d)

        Returns:
            DataFrame with OHLCV data
        """
        pass

    @abstractmethod
    async def get_realtime_bar(
        self,
        symbol: str,
        bar_size: int = 5
    ) -> Optional[MarketData]:
        """
        Get real-time aggregated bar

        Args:
            symbol: Symbol to get bar for
            bar_size: Bar size in seconds

        Returns:
            MarketData for current bar
        """
        pass

    def is_market_hours(self) -> bool:
        """
        Check if currently in market hours

        Returns:
            True if in market hours
        """
        from datetime import datetime
        import pytz

        # Get current time in GMT
        gmt = pytz.timezone('GMT')
        now = datetime.now(gmt)
        current_time = now.time()

        # Market generally open 00:00-21:00 GMT for global markets
        # Specific to instrument types
        market_open = datetime.strptime("00:00", "%H:%M").time()
        market_close = datetime.strptime("21:00", "%H:%M").time()

        return market_open <= current_time <= market_close

    def get_latency(self) -> float:
        """
        Get current data feed latency in milliseconds

        Returns:
            Latency in ms
        """
        # To be implemented by specific providers
        return 0.0
