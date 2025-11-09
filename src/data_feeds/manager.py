"""
Data Feed Manager
Manages multiple data feeds with failover support
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from loguru import logger
import asyncio

from .base import DataFeedBase, MarketData
from .yfinance_feed import YahooFinanceFeed


class DataFeedManager:
    """Manages primary and backup data feeds"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data feed manager

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.primary_feed: Optional[DataFeedBase] = None
        self.backup_feed: Optional[DataFeedBase] = None
        self.current_feed: Optional[DataFeedBase] = None
        self.latency_threshold = config.get('latency_threshold', 100)  # ms

    async def initialize(self) -> bool:
        """
        Initialize primary and backup feeds

        Returns:
            True if at least one feed connects successfully
        """
        try:
            # Initialize primary feed
            primary_type = self.config.get('primary', 'yfinance')
            self.primary_feed = self._create_feed(primary_type)

            if await self.primary_feed.connect():
                self.current_feed = self.primary_feed
                logger.info(f"Primary feed ({primary_type}) connected successfully")
            else:
                logger.error(f"Failed to connect to primary feed ({primary_type})")

            # Initialize backup feed
            backup_type = self.config.get('backup', 'yfinance')
            if backup_type != primary_type:
                self.backup_feed = self._create_feed(backup_type)
                if await self.backup_feed.connect():
                    logger.info(f"Backup feed ({backup_type}) connected successfully")
                else:
                    logger.warning(f"Failed to connect to backup feed ({backup_type})")

            return self.current_feed is not None and self.current_feed.is_connected

        except Exception as e:
            logger.error(f"Failed to initialize data feeds: {e}")
            return False

    def _create_feed(self, feed_type: str) -> DataFeedBase:
        """
        Create data feed instance based on type

        Args:
            feed_type: Type of feed (yfinance, ib, alphavantage, custom)

        Returns:
            DataFeedBase instance
        """
        if feed_type == 'yfinance':
            return YahooFinanceFeed(self.config)
        elif feed_type == 'ib':
            # Import only if needed
            from .ib_feed import InteractiveBrokersFeed
            return InteractiveBrokersFeed(self.config.get('ib', {}))
        elif feed_type == 'alphavantage':
            from .alphavantage_feed import AlphaVantageFeed
            return AlphaVantageFeed(self.config.get('alphavantage', {}))
        elif feed_type == 'custom':
            from .custom_feed import CustomAPIFeed
            return CustomAPIFeed(self.config.get('custom', {}))
        else:
            raise ValueError(f"Unknown feed type: {feed_type}")

    async def failover_to_backup(self) -> bool:
        """
        Switch to backup feed

        Returns:
            True if failover successful
        """
        if self.backup_feed is None:
            logger.error("No backup feed available for failover")
            return False

        try:
            logger.warning("Failing over to backup feed...")

            if not self.backup_feed.is_connected:
                if not await self.backup_feed.connect():
                    logger.error("Failed to connect to backup feed")
                    return False

            # Transfer subscriptions
            if self.current_feed and self.current_feed.subscriptions:
                await self.backup_feed.subscribe(self.current_feed.subscriptions)

            self.current_feed = self.backup_feed
            logger.info("Failover to backup feed successful")
            return True

        except Exception as e:
            logger.error(f"Failover failed: {e}")
            return False

    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to symbols on current feed

        Args:
            symbols: List of symbols

        Returns:
            True if successful
        """
        if self.current_feed is None:
            logger.error("No active feed available")
            return False

        return await self.current_feed.subscribe(symbols)

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price with failover support

        Args:
            symbol: Symbol to get price for

        Returns:
            Current price or None
        """
        if self.current_feed is None:
            logger.error("No active feed available")
            return None

        try:
            price = await self.current_feed.get_current_price(symbol)

            if price is None:
                # Try failover
                if await self.failover_to_backup():
                    price = await self.current_feed.get_current_price(symbol)

            return price

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get market data with failover support

        Args:
            symbol: Symbol to get data for

        Returns:
            MarketData or None
        """
        if self.current_feed is None:
            logger.error("No active feed available")
            return None

        try:
            data = await self.current_feed.get_market_data(symbol)

            if data is None:
                # Try failover
                if await self.failover_to_backup():
                    data = await self.current_feed.get_market_data(symbol)

            return data

        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get prices for multiple symbols concurrently

        Args:
            symbols: List of symbols

        Returns:
            Dictionary mapping symbol to price
        """
        tasks = [self.get_current_price(symbol) for symbol in symbols]
        prices = await asyncio.gather(*tasks)
        return dict(zip(symbols, prices))

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
            symbol: Symbol
            start: Start datetime
            end: End datetime
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        if self.current_feed is None:
            logger.error("No active feed available")
            return pd.DataFrame()

        return await self.current_feed.get_historical_data(symbol, start, end, interval)

    def check_latency(self) -> float:
        """
        Check current feed latency

        Returns:
            Latency in milliseconds
        """
        if self.current_feed is None:
            return float('inf')

        latency = self.current_feed.get_latency()

        # Trigger failover if latency exceeds threshold
        if latency > self.latency_threshold:
            logger.warning(f"High latency detected: {latency}ms (threshold: {self.latency_threshold}ms)")
            asyncio.create_task(self.failover_to_backup())

        return latency

    async def disconnect(self) -> None:
        """Disconnect all feeds"""
        if self.primary_feed:
            await self.primary_feed.disconnect()
        if self.backup_feed:
            await self.backup_feed.disconnect()
        logger.info("All data feeds disconnected")

    def get_feed_status(self) -> Dict[str, Any]:
        """
        Get status of all feeds

        Returns:
            Status dictionary
        """
        return {
            'primary_connected': self.primary_feed.is_connected if self.primary_feed else False,
            'backup_connected': self.backup_feed.is_connected if self.backup_feed else False,
            'current_feed': 'primary' if self.current_feed == self.primary_feed else 'backup',
            'latency': self.check_latency(),
            'subscriptions': self.current_feed.subscriptions if self.current_feed else []
        }
