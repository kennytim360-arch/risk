#!/usr/bin/env python3
"""
One-Page Trading Playbook
Quick reference guide displayed during trading session
"""

from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config


def display_playbook():
    """Display the one-page trading playbook"""

    config = get_config()

    print("\n" + "="*80)
    print(" " * 25 + "RORO QUICK COMMANDS")
    print("="*80)

    print("\n" + "-"*80)
    print("REGIME CHECK:")
    print("-"*80)
    print("SPX ↑ + USDJPY ↑ + VIX ↓ = RISK-ON")
    print("SPX ↓ + USDJPY ↓ + VIX ↑ = RISK-OFF")
    print("MIXED SIGNALS         = STAY OUT")

    print("\n" + "-"*80)
    print("ENTRY TRIGGERS:")
    print("-"*80)
    print("1. Strong Regime + Correlation > 0.7")
    print("2. Clear Divergence + 10-min confirmation")
    print("3. Tier-1 Checklist PASSED")

    print("\n" + "-"*80)
    print("TIER-1 ENTRY CHECKLIST:")
    print("-"*80)
    print("✓ REGIME IDENTIFIED     - Clear Strong/Weak RORO (not Transition)")
    print("✓ CORRELATION HEALTH    - > 0.4 and stable/improving")
    print("✓ NO ADVERSE DIVERGENCE - Unless trading the divergence")
    print("✓ RISK PARAMETERS       - Size calculated, 1:2 R/R min, stop set")

    print("\n" + "-"*80)
    print("RISK CONTROLS:")
    print("-"*80)
    max_trade = config.get('account.max_trade_risk', 0.02)
    max_daily = config.get('account.max_daily_risk', 0.03)
    max_losses = config.get('risk_management.daily_limits.max_losses', 3)

    print(f"- Max Trade:       {max_trade:.1%}")
    print(f"- Max Daily Risk:  {max_daily:.1%}")
    print(f"- Loss Limit:      {max_losses} consecutive losses → STOP")
    print( "- News <30min:     25% size or FLAT")

    print("\n" + "-"*80)
    print("SESSION TIMES (GMT):")
    print("-"*80)
    print("POWER HOURS: 13:00-16:00  (US/Europe overlap - maximum opportunities)")
    print("REDUCE:      19:30        (Reduce to 50% size)")
    print("FLAT BY:     20:55        (Close all positions)")

    print("\n" + "-"*80)
    print("POSITION SIZING QUICK REFERENCE:")
    print("-"*80)
    print("Strong Regime + VIX<15:  Full Size (2%)")
    print("Weak Regime:             Half Size (1%)")
    print("Transition/Divergence:   Quarter Size (0.5%)")
    print("Correlation Broken:      NO TRADE")

    print("\n" + "-"*80)
    print("STOP LOSS GUIDE:")
    print("-"*80)
    print("Strong Regime:  Initial 0.5% → Trail 0.3% after +0.5%")
    print("Weak Regime:    Initial 0.3% → Trail 0.2% after +0.3%")
    print("Divergence:     Initial 0.25% → 30-min time stop")

    print("\n" + "-"*80)
    print("DIVERGENCE SIGNALS:")
    print("-"*80)
    print("BULLISH: SPX new low + USDJPY higher low + VIX flat/down + 10min confirm")
    print("BEARISH: SPX new high + USDJPY lower high + DXY up + 10min confirm")
    print("→ Counter-trend trade: Max 50% size, tight stops, 30-60min reversal expected")

    print("\n" + "-"*80)
    print("EMERGENCY PROTOCOLS:")
    print("-"*80)
    print("Data Feed Failure:    Flatten → Switch to backup → Stop if not resolved in 5min")
    print("Black Swan (>3%/5min): Auto-flatten → Suspend 1 hour → Resume at 25% size")
    print("3 Consecutive Losses: STOP TRADING for session")

    print("\n" + "-"*80)
    print("TRADING PSYCHOLOGY REMINDERS:")
    print("-"*80)
    print("• Follow the checklist EVERY time - no exceptions")
    print("• When in doubt, stay out - missed opportunity < bad trade")
    print("• Respect the stops - they exist for a reason")
    print("• Size down in uncertainty - you can always add later")
    print("• If feeling emotional - reduce size or take a break")

    print("\n" + "="*80)
    print(f"Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT')}")
    print("="*80 + "\n")

    print("Keep this window visible during your trading session!")
    print("Press Ctrl+C to exit\n")


def main():
    """Main entry point"""
    try:
        display_playbook()

        # Keep open
        input("Press Enter to close playbook...")

    except KeyboardInterrupt:
        print("\n\nPlaybook closed. Trade well!")


if __name__ == '__main__':
    main()
