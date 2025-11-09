"""
Yahoo Finance Data Feed Implementation
Free data provider for development and basic use
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio

from .base import DataFeedBase, MarketData


class YahooFinanceFeed(DataFeedBase):
    """Yahoo Finance data feed implementation"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Yahoo Finance feed

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.tickers: Dict[str, yf.Ticker] = {}
        self.cache: Dict[str, MarketData] = {}
        self.cache_duration = 5  # seconds

    async def connect(self) -> bool:
        """
        Connect to Yahoo Finance

        Returns:
            True (Yahoo Finance doesn't require authentication)
        """
        try:
            # Test connection with a simple query
            test = yf.Ticker("SPY")
            _ = test.info
            self.is_connected = True
            logger.info("Connected to Yahoo Finance")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Yahoo Finance: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Yahoo Finance"""
        self.is_connected = False
        self.tickers.clear()
        self.cache.clear()
        logger.info("Disconnected from Yahoo Finance")

    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to symbols (create Ticker objects)

        Args:
            symbols: List of symbols

        Returns:
            True if successful
        """
        try:
            for symbol in symbols:
                if symbol not in self.tickers:
                    self.tickers[symbol] = yf.Ticker(symbol)
                    self.subscriptions.append(symbol)
            logger.info(f"Subscribed to {len(symbols)} symbols")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to symbols: {e}")
            return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from symbols

        Args:
            symbols: List of symbols

        Returns:
            True if successful
        """
        for symbol in symbols:
            if symbol in self.tickers:
                del self.tickers[symbol]
            if symbol in self.subscriptions:
                self.subscriptions.remove(symbol)
            if symbol in self.cache:
                del self.cache[symbol]
        logger.info(f"Unsubscribed from {len(symbols)} symbols")
        return True

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for symbol

        Args:
            symbol: Symbol to get price for

        Returns:
            Current price or None
        """
        try:
            if symbol not in self.tickers:
                await self.subscribe([symbol])

            # Use fast_info for quick price access
            ticker = self.tickers[symbol]
            price = ticker.fast_info.get('lastPrice')

            if price is None:
                # Fallback to history
                hist = ticker.history(period='1d', interval='1m')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]

            return float(price) if price is not None else None

        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get current market data snapshot

        Args:
            symbol: Symbol to get data for

        Returns:
            MarketData object or None
        """
        try:
            # Check cache
            if symbol in self.cache:
                cached = self.cache[symbol]
                age = (datetime.now() - cached.timestamp).total_seconds()
                if age < self.cache_duration:
                    return cached

            # Get fresh data
            if symbol not in self.tickers:
                await self.subscribe([symbol])

            ticker = self.tickers[symbol]

            # Get latest 1-minute bar
            hist = ticker.history(period='1d', interval='1m')

            if hist.empty:
                return None

            latest = hist.iloc[-1]

            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                open=float(latest['Open']),
                high=float(latest['High']),
                low=float(latest['Low']),
                close=float(latest['Close']),
                volume=float(latest['Volume']),
                vwap=None  # Calculate if needed
            )

            # Calculate VWAP if volume data available
            if len(hist) > 0:
                typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
                vwap = (typical_price * hist['Volume']).sum() / hist['Volume'].sum()
                market_data.vwap = float(vwap)

            # Update cache
            self.cache[symbol] = market_data

            return market_data

        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None

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
        try:
            if symbol not in self.tickers:
                await self.subscribe([symbol])

            ticker = self.tickers[symbol]

            # Yahoo Finance interval mapping
            yf_interval = interval
            if interval == '1m':
                yf_interval = '1m'
            elif interval == '5m':
                yf_interval = '5m'
            elif interval == '15m':
                yf_interval = '15m'
            elif interval == '1h':
                yf_interval = '1h'
            elif interval == '1d':
                yf_interval = '1d'

            hist = ticker.history(start=start, end=end, interval=yf_interval)

            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return pd.DataFrame()

            # Standardize column names
            hist.columns = [col.lower() for col in hist.columns]

            return hist

        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()

    async def get_realtime_bar(
        self,
        symbol: str,
        bar_size: int = 5
    ) -> Optional[MarketData]:
        """
        Get real-time aggregated bar

        Args:
            symbol: Symbol to get bar for
            bar_size: Bar size in seconds (limited by Yahoo's 1m minimum)

        Returns:
            MarketData for current bar
        """
        # Yahoo Finance doesn't support sub-minute bars
        # Return latest 1-minute bar as approximation
        return await self.get_market_data(symbol)

    def get_latency(self) -> float:
        """
        Get current data feed latency

        Returns:
            Estimated latency in ms (Yahoo Finance is slow)
        """
        # Yahoo Finance typically has 1-5 second latency
        return 2000.0  # 2 seconds average
