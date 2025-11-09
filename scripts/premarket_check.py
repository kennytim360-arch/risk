#!/usr/bin/env python3
"""
Pre-Market Checklist Script
Runs essential pre-market analysis and system checks
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import setup_logger
from loguru import logger


async def check_data_feeds() -> bool:
    """Check if data feeds are operational"""
    logger.info("Checking data feeds...")

    from src.data_feeds.manager import DataFeedManager

    config = get_config()
    data_feed_config = config.get('data_feed', {})

    feed_manager = DataFeedManager(data_feed_config)

    if not await feed_manager.initialize():
        logger.error("❌ Data feeds failed to connect")
        return False

    status = feed_manager.get_feed_status()

    if status['primary_connected']:
        logger.info(f"✓ Primary feed connected ({status['current_feed']})")
    else:
        logger.warning("⚠ Primary feed not connected")

    if status['backup_connected']:
        logger.info("✓ Backup feed connected")

    await feed_manager.disconnect()

    return status['primary_connected']


async def check_overnight_action() -> dict:
    """Analyze overnight market action"""
    logger.info("Analyzing overnight action...")

    from src.data_feeds.manager import DataFeedManager

    config = get_config()
    data_feed_config = config.get('data_feed', {})

    feed_manager = DataFeedManager(data_feed_config)
    await feed_manager.initialize()

    # Get yesterday's close and current price
    symbols = ['^GSPC', 'USDJPY=X', '^VIX']
    results = {}

    for symbol in symbols:
        # Get historical data
        end = datetime.now()
        start = end - timedelta(days=2)

        hist = await feed_manager.get_historical_data(symbol, start, end, '1d')

        if not hist.empty and len(hist) >= 2:
            prev_close = hist['close'].iloc[-2]
            current = hist['close'].iloc[-1]
            change = (current - prev_close) / prev_close

            results[symbol] = {
                'previous_close': prev_close,
                'current': current,
                'change_pct': change
            }

            logger.info(f"{symbol}: {change:+.2%}")

    await feed_manager.disconnect()

    return results


def check_economic_calendar() -> dict:
    """Check for high-impact events today"""
    logger.info("Checking economic calendar...")

    # In production, would integrate with economic calendar API
    # For now, return placeholder

    logger.info("⚠ Manual check required: Review economic calendar for HIA events")

    return {
        'checked': True,
        'high_impact_events': [],
        'note': 'Manual verification required'
    }


def check_system_health() -> dict:
    """Verify system components are healthy"""
    logger.info("Checking system health...")

    health = {
        'config_loaded': False,
        'log_directory': False,
        'data_directory': False
    }

    try:
        config = get_config()
        health['config_loaded'] = True
        logger.info("✓ Configuration loaded")
    except Exception as e:
        logger.error(f"❌ Config error: {e}")

    # Check directories
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    health['log_directory'] = log_dir.exists()
    logger.info(f"✓ Log directory: {log_dir}")

    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    health['data_directory'] = data_dir.exists()
    logger.info(f"✓ Data directory: {data_dir}")

    return health


def mental_readiness_check() -> dict:
    """Interactive mental readiness assessment"""
    print("\n" + "="*60)
    print("MENTAL READINESS CHECK")
    print("="*60)

    print("\nRate yourself on a scale of 1-10:")

    try:
        confidence = int(input("Confidence level (need >7 for full size): "))
        focus = int(input("Focus/Concentration level: "))
        rest = int(input("Rest level (how well rested): "))

        emotional_state = input("Emotional state (calm/focused/anxious/other): ").lower()

        ready = confidence >= 7 and focus >= 7 and rest >= 7

        if ready and emotional_state in ['calm', 'focused']:
            recommendation = "FULL SIZE APPROVED"
        elif confidence >= 5 and focus >= 5:
            recommendation = "50% SIZE RECOMMENDED"
        else:
            recommendation = "PAPER TRADING ONLY"

        print(f"\nRecommendation: {recommendation}")

        return {
            'confidence': confidence,
            'focus': focus,
            'rest': rest,
            'emotional_state': emotional_state,
            'recommendation': recommendation
        }

    except (ValueError, KeyboardInterrupt):
        print("\nSkipping mental readiness check")
        return {'skipped': True}


def calculate_key_levels(overnight_data: dict) -> dict:
    """Calculate key support/resistance levels"""
    logger.info("Calculating key levels...")

    levels = {}

    for symbol, data in overnight_data.items():
        current = data['current']

        # Simple levels (would be more sophisticated in production)
        levels[symbol] = {
            'current': current,
            'resistance': current * 1.01,  # 1% above
            'support': current * 0.99,  # 1% below
            'vwap': current  # Would calculate actual VWAP from intraday data
        }

    return levels


async def main():
    """Run pre-market checklist"""
    setup_logger(level='INFO')

    print("\n" + "="*60)
    print("RORO TRADING SYSTEM - PRE-MARKET CHECKLIST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

    results = {}

    # 1. System Health
    print("\n[1/5] SYSTEM HEALTH CHECK")
    print("-" * 60)
    results['system_health'] = check_system_health()

    # 2. Data Feeds
    print("\n[2/5] DATA FEEDS CHECK")
    print("-" * 60)
    results['data_feeds'] = await check_data_feeds()

    # 3. Overnight Action
    print("\n[3/5] OVERNIGHT ACTION")
    print("-" * 60)
    results['overnight'] = await check_overnight_action()

    # 4. Economic Calendar
    print("\n[4/5] ECONOMIC CALENDAR")
    print("-" * 60)
    results['calendar'] = check_economic_calendar()

    # 5. Mental Readiness
    print("\n[5/5] MENTAL READINESS")
    print("-" * 60)
    results['mental'] = mental_readiness_check()

    # Calculate key levels
    if results['overnight']:
        results['key_levels'] = calculate_key_levels(results['overnight'])

    # Summary
    print("\n" + "="*60)
    print("PRE-MARKET CHECKLIST SUMMARY")
    print("="*60)

    all_clear = (
        results['system_health']['config_loaded'] and
        results['data_feeds']
    )

    if all_clear:
        print("✓ ALL SYSTEMS GO")
    else:
        print("⚠ REVIEW ISSUES BEFORE TRADING")

    if 'mental' in results and not results['mental'].get('skipped'):
        print(f"\nTrading Recommendation: {results['mental']['recommendation']}")

    print("\n" + "="*60)
    print("Ready to trade. Good luck!")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
