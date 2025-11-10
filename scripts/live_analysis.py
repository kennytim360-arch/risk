#!/usr/bin/env python3
"""
RORO Market Analysis Dashboard
Live analysis only - NO TRADING
Shows regime, correlation, divergence, and trading recommendations
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import setup_logger
from src.data_feeds.manager import DataFeedManager
from src.regime.classifier import RegimeClassifier, RegimeType
from src.correlation.analyzer import CorrelationAnalyzer, CorrelationHealth
from src.divergence.detector import DivergenceDetector, DivergenceType
from src.position.calculator import PositionSizeCalculator
from loguru import logger


def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print dashboard header"""
    print("\n" + "="*80)
    print(" "*25 + "RORO LIVE MARKET ANALYSIS")
    print(" "*28 + "Analysis Only - No Trading")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


def print_regime_analysis(regime, trading_bias):
    """Print regime classification analysis"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*25 + "MARKET REGIME ANALYSIS" + " "*31 + "│")
    print("├" + "─"*78 + "┤")

    regime_type = regime.regime_type.value
    confidence = regime.confidence

    # Color coding based on regime
    if regime_type == "STRONG_RISK_ON":
        indicator = "🟢 STRONG RISK-ON"
        bias = "BULLISH - Go LONG on indices"
    elif regime_type == "WEAK_RISK_ON":
        indicator = "🟡 WEAK RISK-ON"
        bias = "MILDLY BULLISH - Reduced size"
    elif regime_type == "TRANSITION":
        indicator = "⚪ TRANSITION ZONE"
        bias = "NEUTRAL - Stay out"
    elif regime_type == "WEAK_RISK_OFF":
        indicator = "🟡 WEAK RISK-OFF"
        bias = "MILDLY BEARISH - Consider shorts"
    else:  # STRONG_RISK_OFF
        indicator = "🔴 STRONG RISK-OFF"
        bias = "BEARISH - Go SHORT on indices"

    print(f"│ Regime: {indicator:<67}│")
    print(f"│ Confidence: {confidence:.1%}{' '*62}│")
    print(f"│ Trading Bias: {bias:<62}│")
    print(f"│ VIX Level: {regime.vix_level:.2f} (Multiplier: {regime.vix_multiplier:.2f}x){' '*32}│")
    print("├" + "─"*78 + "┤")

    # Show individual signals
    print("│ Signal Breakdown:" + " "*59 + "│")
    for signal in regime.signals:
        signal_icon = "↑" if signal.signal_type == "bullish" else "↓" if signal.signal_type == "bearish" else "→"
        strength_bar = "█" * int(signal.strength * 10)
        print(f"│   {signal.instrument:8s} {signal_icon} {strength_bar:<10s} {signal.strength:.0%}{' '*42}│")

    print("└" + "─"*78 + "┘\n")


def print_correlation_analysis(correlation_result, health):
    """Print correlation analysis"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*24 + "CORRELATION ANALYSIS" + " "*34 + "│")
    print("├" + "─"*78 + "┤")

    if correlation_result:
        corr_value = correlation_result.coefficient

        # Health indicator
        if health == CorrelationHealth.HEALTHY:
            health_icon = "🟢 HEALTHY"
            recommendation = "Full size trading approved"
        elif health == CorrelationHealth.DEGRADED:
            health_icon = "🟡 DEGRADED"
            recommendation = "Reduce to 50% size"
        else:
            health_icon = "🔴 BROKEN"
            recommendation = "NO TRADING - Wait for reset"

        print(f"│ US500 ↔ USDJPY Correlation: {corr_value:+.3f}{' '*44}│")
        print(f"│ Status: {health_icon:<66}│")
        print(f"│ Recommendation: {recommendation:<60}│")
        print(f"│ Sample Size: {correlation_result.sample_size} data points{' '*43}│")
    else:
        print("│ Status: 🔴 INSUFFICIENT DATA" + " "*48 + "│")
        print("│ Recommendation: NO TRADING - Building correlation history" + " "*17 + "│")

    print("└" + "─"*78 + "┘\n")


def print_divergence_analysis(divergence):
    """Print divergence detection analysis"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*24 + "DIVERGENCE DETECTION" + " "*34 + "│")
    print("├" + "─"*78 + "┤")

    if divergence:
        if divergence.type == DivergenceType.BULLISH:
            div_icon = "🔵 BULLISH DIVERGENCE DETECTED"
            signal = "Potential reversal UP"
        else:
            div_icon = "🟠 BEARISH DIVERGENCE DETECTED"
            signal = "Potential reversal DOWN"

        print(f"│ {div_icon:<75}│")
        print(f"│ Confidence: {divergence.confidence:.0%}{' '*63}│")
        print(f"│ Signal: {signal:<68}│")
        print(f"│ US500: {divergence.us500_level:.2f}{' '*62}│")
        print(f"│ USDJPY: {divergence.usdjpy_level:.2f}{' '*61}│")
        print(f"│ VIX: {divergence.vix_level:.2f}{' '*68}│")
        print(f"│ Persistence: {divergence.persistence_minutes} minutes{' '*49}│")
        print(f"│ Expected Reversal: Within {divergence.expected_reversal_time} minutes{' '*36}│")
        print("│" + " "*78 + "│")
        print("│ ⚠️  COUNTER-TREND TRADE - Use 50% max size, tight stops" + " "*21 + "│")
    else:
        print("│ Status: ⚪ No divergence detected" + " "*44 + "│")
        print("│ Market: Trend-following mode" + " "*48 + "│")

    print("└" + "─"*78 + "┘\n")


def print_market_data(market_data):
    """Print current market prices"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*28 + "CURRENT PRICES" + " "*36 + "│")
    print("├" + "─"*78 + "┤")

    for instrument, data in market_data.items():
        change = ((data.close - data.open) / data.open * 100) if data.open != 0 else 0
        change_icon = "↑" if change > 0 else "↓" if change < 0 else "→"

        print(f"│ {instrument:8s}: {data.close:>10.2f}  {change_icon} {change:+.2f}%{' '*40}│")

    print("└" + "─"*78 + "┘\n")


def print_position_recommendation(regime, vix_level, correlation_health, divergence):
    """Print position sizing recommendation"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*23 + "POSITION SIZE GUIDANCE" + " "*33 + "│")
    print("├" + "─"*78 + "┤")

    # Calculate hypothetical position size (for $100k account)
    account = 100000
    calc = PositionSizeCalculator(get_config())

    if divergence and divergence.confidence > 0.6:
        pos_size = calc.calculate_for_divergence(account, vix_level, correlation_health)
        trade_type = "DIVERGENCE TRADE"
    else:
        pos_size = calc.calculate_position_size(
            account, regime.regime_type, vix_level, correlation_health
        )
        trade_type = "REGIME TRADE"

    print(f"│ Trade Type: {trade_type:<64}│")
    print(f"│ Recommended Size: {pos_size.size:.2%} of account{' '*45}│")
    print(f"│ Risk Amount: ${pos_size.risk_amount:,.2f}{' '*53}│")
    print(f"│ Contracts: {pos_size.contracts}{' '*65}│")
    print("│" + " "*78 + "│")
    print("│ Multipliers Applied:" + " "*57 + "│")
    print(f"│   • Regime: {pos_size.regime_multiplier:.2f}x{' '*62}│")
    print(f"│   • VIX: {pos_size.vix_multiplier:.2f}x{' '*65}│")
    print(f"│   • Correlation: {pos_size.correlation_multiplier:.2f}x{' '*56}│")

    # Recommended stop loss
    stop = calc.get_recommended_stop_loss(regime.regime_type, divergence is not None)
    print(f"│ Recommended Stop Loss: {stop:.2%}{' '*52}│")

    print("└" + "─"*78 + "┘\n")


def print_trading_checklist(regime, correlation_health, divergence):
    """Print Tier-1 entry checklist status"""
    print("┌" + "─"*78 + "┐")
    print("│" + " "*23 + "TIER-1 ENTRY CHECKLIST" + " "*32 + "│")
    print("├" + "─"*78 + "┤")

    # Check 1: Regime identified
    regime_ok = regime.regime_type != RegimeType.TRANSITION
    check1 = "✓" if regime_ok else "✗"
    print(f"│ {check1} REGIME IDENTIFIED: {regime.regime_type.value:<51}│")

    # Check 2: Correlation health
    corr_ok = correlation_health != CorrelationHealth.BROKEN
    check2 = "✓" if corr_ok else "✗"
    print(f"│ {check2} CORRELATION HEALTH: {correlation_health.value:<50}│")

    # Check 3: Divergence check
    if divergence:
        check3 = "⚠"
        div_status = f"Trading divergence ({divergence.type.value})"
    else:
        check3 = "✓"
        div_status = "No adverse divergence"
    print(f"│ {check3} DIVERGENCE: {div_status:<60}│")

    # Check 4: Overall clearance
    all_clear = regime_ok and corr_ok
    check4 = "✓" if all_clear else "✗"

    if all_clear:
        status = "APPROVED FOR TRADING"
        color = "🟢"
    else:
        status = "NO TRADE - Wait for better conditions"
        color = "🔴"

    print("│" + " "*78 + "│")
    print(f"│ {color} OVERALL: {status:<63}│")

    print("└" + "─"*78 + "┘\n")


def print_footer():
    """Print dashboard footer"""
    print("─"*80)
    print("Press Ctrl+C to exit | Updates every 5 seconds | ANALYSIS ONLY - No orders placed")
    print("─"*80 + "\n")


async def run_analysis_dashboard():
    """Run the live market analysis dashboard"""

    # Initialize
    config = get_config()
    setup_logger(level='INFO')

    # Initialize components
    data_feed_config = config.get('data_feed', {})
    data_feed = DataFeedManager(data_feed_config)

    if not await data_feed.initialize():
        print("❌ Failed to initialize data feeds")
        return

    # Subscribe to instruments
    instruments_config = config.get('instruments', {}).get('primary', [])
    symbols = [inst.get('symbol') for inst in instruments_config]
    await data_feed.subscribe(symbols)

    # Initialize analyzers
    regime_classifier = RegimeClassifier(config)
    correlation_analyzer = CorrelationAnalyzer(config)
    divergence_detector = DivergenceDetector(config)

    print("\n✓ Market Analysis Dashboard initialized successfully!\n")
    print("Starting live analysis...\n")

    await asyncio.sleep(2)

    # Main analysis loop
    try:
        while True:
            # Fetch market data
            market_data = {}
            for inst in instruments_config:
                symbol = inst.get('symbol')
                internal_name = inst.get('internal_name')
                data = await data_feed.get_market_data(symbol)
                if data:
                    market_data[internal_name] = data

            if not market_data:
                print("⚠️  Waiting for market data...")
                await asyncio.sleep(5)
                continue

            # Run analysis
            regime = regime_classifier.classify_regime(market_data)

            correlation_analyzer.update_prices(market_data)
            correlation = correlation_analyzer.get_primary_correlation()
            correlation_health = correlation_analyzer.get_overall_health()

            divergence = divergence_detector.detect_divergence(market_data)

            trading_bias = regime_classifier.get_regime_trading_bias()

            # Display dashboard
            clear_screen()
            print_header()
            print_market_data(market_data)
            print_regime_analysis(regime, trading_bias)
            print_correlation_analysis(correlation, correlation_health)
            print_divergence_analysis(divergence)
            print_position_recommendation(regime, regime.vix_level, correlation_health, divergence)
            print_trading_checklist(regime, correlation_health, divergence)
            print_footer()

            # Wait before next update
            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\n\n✓ Analysis dashboard stopped by user")
    finally:
        await data_feed.disconnect()


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print(" "*25 + "RORO MARKET ANALYSIS DASHBOARD")
    print(" "*30 + "Starting up...")
    print("="*80)

    asyncio.run(run_analysis_dashboard())


if __name__ == '__main__':
    main()
