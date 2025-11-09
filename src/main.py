"""
RORO Trading System - Main Application
Entry point for live trading, paper trading, and backtesting
"""

import asyncio
import argparse
from datetime import datetime
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import setup_logger
from src.data_feeds.manager import DataFeedManager
from src.regime.classifier import RegimeClassifier
from src.correlation.analyzer import CorrelationAnalyzer
from src.divergence.detector import DivergenceDetector
from src.position.calculator import PositionSizeCalculator
from src.risk.manager import RiskManager


class ROROTradingSystem:
    """Main RORO trading system coordinator"""

    def __init__(self, mode: str = 'paper'):
        """
        Initialize trading system

        Args:
            mode: Operating mode (live, paper, backtest)
        """
        self.mode = mode
        self.config = get_config()

        # Setup logging
        log_config = self.config.get('logging', {})
        setup_logger(
            level=log_config.get('level', 'INFO'),
            rotation=log_config.get('rotation', '1 day'),
            retention=log_config.get('retention', '30 days')
        )

        logger.info(f"Initializing RORO Trading System - Mode: {mode}")

        # Initialize components
        self.data_feed: Optional[DataFeedManager] = None
        self.regime_classifier: Optional[RegimeClassifier] = None
        self.correlation_analyzer: Optional[CorrelationAnalyzer] = None
        self.divergence_detector: Optional[DivergenceDetector] = None
        self.position_calculator: Optional[PositionSizeCalculator] = None
        self.risk_manager: Optional[RiskManager] = None

        # System state
        self.is_running = False
        self.instruments = ['US500', 'USDJPY', 'VIX', 'US10Y', 'DXY']

    async def initialize(self) -> bool:
        """
        Initialize all system components

        Returns:
            True if successful
        """
        try:
            logger.info("Initializing system components...")

            # Initialize data feed manager
            data_feed_config = self.config.get('data_feed', {})
            self.data_feed = DataFeedManager(data_feed_config)

            if not await self.data_feed.initialize():
                logger.error("Failed to initialize data feeds")
                return False

            # Subscribe to instruments
            instruments_config = self.config.get('instruments', {}).get('primary', [])
            symbols = [inst.get('symbol') for inst in instruments_config]

            if not await self.data_feed.subscribe(symbols):
                logger.error("Failed to subscribe to instruments")
                return False

            # Initialize regime classifier
            self.regime_classifier = RegimeClassifier(self.config)

            # Initialize correlation analyzer
            self.correlation_analyzer = CorrelationAnalyzer(self.config)

            # Initialize divergence detector
            self.divergence_detector = DivergenceDetector(self.config)

            # Initialize position calculator
            self.position_calculator = PositionSizeCalculator(self.config)

            # Initialize risk manager
            self.risk_manager = RiskManager(self.config)

            logger.info("All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def update_market_data(self) -> dict:
        """
        Fetch latest market data for all instruments

        Returns:
            Dictionary of instrument -> MarketData
        """
        market_data = {}

        instruments_config = self.config.get('instruments', {}).get('primary', [])

        for inst in instruments_config:
            symbol = inst.get('symbol')
            internal_name = inst.get('internal_name')

            data = await self.data_feed.get_market_data(symbol)

            if data:
                market_data[internal_name] = data

        return market_data

    async def analyze_market(self, market_data: dict) -> dict:
        """
        Run complete market analysis

        Args:
            market_data: Dictionary of market data

        Returns:
            Analysis results dictionary
        """
        analysis = {}

        # Regime classification
        regime = self.regime_classifier.classify_regime(market_data)
        analysis['regime'] = regime

        # Correlation analysis
        self.correlation_analyzer.update_prices(market_data)
        correlation = self.correlation_analyzer.get_primary_correlation()
        correlation_health = self.correlation_analyzer.get_overall_health()
        analysis['correlation'] = correlation
        analysis['correlation_health'] = correlation_health

        # Divergence detection
        divergence = self.divergence_detector.detect_divergence(market_data)
        analysis['divergence'] = divergence

        # Get trading bias
        trading_bias = self.regime_classifier.get_regime_trading_bias()
        analysis['trading_bias'] = trading_bias

        return analysis

    async def generate_signals(self, analysis: dict, market_data: dict) -> list:
        """
        Generate trading signals based on analysis

        Args:
            analysis: Market analysis results
            market_data: Current market data

        Returns:
            List of trading signals
        """
        signals = []

        regime = analysis['regime']
        correlation_health = analysis['correlation_health']
        divergence = analysis['divergence']

        # Check if can trade based on correlation
        can_trade, reason = self.correlation_analyzer.should_trade()

        if not can_trade:
            logger.info(f"No trading: {reason}")
            return signals

        # Check risk manager
        risk_status = self.risk_manager.get_status()
        if not risk_status['can_trade']:
            logger.info(f"No trading: Risk manager status {risk_status['current_status']}")
            return signals

        # Generate signals based on regime and divergence
        vix_level = market_data.get('VIX').close if 'VIX' in market_data else 20.0

        # Regime-based signals
        if regime.confidence > 0.7:
            trading_bias = analysis['trading_bias']

            if trading_bias.get('action') in ['LONG', 'SHORT']:
                # Calculate position size
                pos_size = self.position_calculator.calculate_position_size(
                    account_balance=self.risk_manager.current_balance,
                    regime_type=regime.regime_type,
                    vix_level=vix_level,
                    correlation_health=correlation_health
                )

                signal = {
                    'type': 'REGIME',
                    'action': trading_bias['action'],
                    'instruments': trading_bias.get('primary_instruments', []),
                    'position_size': pos_size,
                    'regime': regime.regime_type.value,
                    'confidence': regime.confidence,
                    'timestamp': datetime.now()
                }

                signals.append(signal)

        # Divergence-based signals
        if divergence and divergence.confidence > 0.6:
            pos_size = self.position_calculator.calculate_for_divergence(
                account_balance=self.risk_manager.current_balance,
                vix_level=vix_level,
                correlation_health=correlation_health
            )

            signal = {
                'type': 'DIVERGENCE',
                'action': 'LONG' if divergence.type.value == 'BULLISH' else 'SHORT',
                'instruments': ['US500'],  # Primary instrument for divergence
                'position_size': pos_size,
                'divergence_type': divergence.type.value,
                'confidence': divergence.confidence,
                'expected_reversal': divergence.expected_reversal_time,
                'timestamp': datetime.now()
            }

            signals.append(signal)

        return signals

    async def trading_loop(self) -> None:
        """Main trading loop"""
        logger.info("Starting trading loop...")

        update_interval = 5  # Update every 5 seconds

        while self.is_running:
            try:
                # Update market data
                market_data = await self.update_market_data()

                if not market_data:
                    logger.warning("No market data available")
                    await asyncio.sleep(update_interval)
                    continue

                # Analyze market
                analysis = await self.analyze_market(market_data)

                # Log current state
                logger.info(
                    f"Regime: {analysis['regime'].regime_type.value} "
                    f"({analysis['regime'].confidence:.2f}) | "
                    f"Correlation: {analysis['correlation_health'].value}"
                )

                if analysis['divergence']:
                    logger.info(
                        f"Divergence: {analysis['divergence'].type.value} "
                        f"({analysis['divergence'].confidence:.2f})"
                    )

                # Generate trading signals
                signals = await self.generate_signals(analysis, market_data)

                if signals:
                    logger.info(f"Generated {len(signals)} trading signals")
                    for signal in signals:
                        logger.info(f"  Signal: {signal['type']} - {signal['action']}")

                # Update active positions (check stops, etc.)
                await self.update_positions(market_data)

                await asyncio.sleep(update_interval)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(update_interval)

    async def update_positions(self, market_data: dict) -> None:
        """
        Update active positions (check stops, trailing stops)

        Args:
            market_data: Current market data
        """
        # Get current regime
        regime = self.regime_classifier.current_regime

        if not regime:
            return

        # Check each active trade
        for trade_id, trade in list(self.risk_manager.active_trades.items()):
            # Get current price for instrument
            inst_data = market_data.get(trade.instrument)

            if not inst_data:
                continue

            current_price = inst_data.close

            # Check stop loss
            if self.risk_manager.check_stop_loss(trade_id, current_price):
                logger.warning(f"Stop loss hit for {trade_id}")
                self.risk_manager.close_trade(trade_id, current_price, "Stop Loss")
                continue

            # Update trailing stop
            self.risk_manager.update_trailing_stop(
                trade_id,
                current_price,
                regime.regime_type
            )

    async def run(self) -> None:
        """Run the trading system"""
        if not await self.initialize():
            logger.error("Failed to initialize system")
            return

        self.is_running = True

        try:
            if self.mode == 'backtest':
                logger.info("Backtesting mode not yet implemented")
                # await self.run_backtest()
            else:
                await self.trading_loop()

        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown system gracefully"""
        logger.info("Shutting down system...")

        self.is_running = False

        # Close all positions in live mode
        if self.mode == 'live':
            logger.warning("Closing all positions before shutdown")
            self.risk_manager.emergency_flatten_all("System Shutdown")

        # Disconnect data feeds
        if self.data_feed:
            await self.data_feed.disconnect()

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='RORO Trading System')

    parser.add_argument(
        '--mode',
        choices=['live', 'paper', 'backtest'],
        default='paper',
        help='Operating mode'
    )

    parser.add_argument(
        '--start',
        type=str,
        help='Start date for backtesting (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end',
        type=str,
        help='End date for backtesting (YYYY-MM-DD)'
    )

    args = parser.parse_args()

    # Create and run system
    system = ROROTradingSystem(mode=args.mode)

    # Run async
    asyncio.run(system.run())


if __name__ == '__main__':
    main()
