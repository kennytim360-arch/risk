"""
Risk Management Module
Implements stop losses, daily limits, and emergency protocols
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger

from ..regime.classifier import RegimeType
from ..utils.config import ConfigManager


class RiskStatus(Enum):
    """Risk status levels"""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    LOCKED = "LOCKED"


@dataclass
class TradeRecord:
    """Record of individual trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    instrument: str
    direction: str  # 'LONG' or 'SHORT'
    size: float
    entry_price: float
    exit_price: Optional[float]
    stop_loss: float
    take_profit: Optional[float]
    pnl: Optional[float]
    is_winner: Optional[bool]


class RiskManager:
    """Comprehensive risk management system"""

    def __init__(self, config: ConfigManager):
        """
        Initialize risk manager

        Args:
            config: Configuration manager
        """
        self.config = config
        self.risk_config = config.get('risk_management', {})
        self.account_config = config.get('account', {})

        # Account parameters
        self.initial_capital = self.account_config.get('initial_capital', 100000.0)
        self.current_balance = self.initial_capital

        # Risk limits
        self.max_trade_risk = self.account_config.get('max_trade_risk', 0.02)
        self.max_daily_risk = self.account_config.get('max_daily_risk', 0.03)

        # Loss limits
        self.max_consecutive_losses = self.risk_config.get('daily_limits', {}).get('max_losses', 3)
        self.max_daily_drawdown = self.risk_config.get('daily_limits', {}).get('max_drawdown', 0.03)

        # Trading state
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_trades: List[TradeRecord] = []
        self.active_trades: Dict[str, TradeRecord] = {}

        # Risk status
        self.current_status = RiskStatus.NORMAL
        self.locked_until: Optional[datetime] = None

        # Session tracking
        self.session_start_balance = self.initial_capital
        self.last_reset_time = datetime.now()

    def reset_daily_stats(self) -> None:
        """Reset daily statistics (called at start of new day)"""
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_trades = []
        self.session_start_balance = self.current_balance
        self.last_reset_time = datetime.now()
        self.current_status = RiskStatus.NORMAL
        logger.info("Daily risk stats reset")

    def check_daily_reset(self) -> None:
        """Check if daily reset is needed"""
        reset_time = self.risk_config.get('daily_limits', {}).get('reset_time', '00:00')
        from datetime import datetime
        now = datetime.now()
        reset_hour, reset_minute = map(int, reset_time.split(':'))

        # If past reset time and last reset was before today's reset time
        if now.hour >= reset_hour and now.minute >= reset_minute:
            if self.last_reset_time.date() < now.date():
                self.reset_daily_stats()

    def can_open_trade(
        self,
        instrument: str,
        size: float,
        stop_loss_percent: float
    ) -> Tuple[bool, str]:
        """
        Check if new trade can be opened

        Args:
            instrument: Instrument to trade
            size: Position size as percentage
            stop_loss_percent: Stop loss percentage

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check if locked
        if self.locked_until and datetime.now() < self.locked_until:
            return (False, f"Risk manager locked until {self.locked_until}")

        # Check daily reset
        self.check_daily_reset()

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.current_status = RiskStatus.LOCKED
            return (False, f"Max consecutive losses reached: {self.consecutive_losses}")

        # Check daily drawdown
        daily_dd_pct = self.daily_pnl / self.session_start_balance if self.session_start_balance > 0 else 0

        if daily_dd_pct < -self.max_daily_drawdown:
            self.current_status = RiskStatus.LOCKED
            return (False, f"Max daily drawdown reached: {daily_dd_pct:.2%}")

        # Check position size risk
        risk_amount = self.current_balance * size * stop_loss_percent

        if size > self.max_trade_risk:
            return (False, f"Position size {size:.2%} exceeds max {self.max_trade_risk:.2%}")

        # Check if would exceed daily risk
        if abs(daily_dd_pct) + (risk_amount / self.session_start_balance) > self.max_daily_risk:
            return (False, "Would exceed max daily risk")

        # Check max positions
        max_positions = self.account_config.get('max_positions', 5)
        if len(self.active_trades) >= max_positions:
            return (False, f"Max positions reached: {max_positions}")

        return (True, "OK")

    def open_trade(
        self,
        instrument: str,
        direction: str,
        size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None
    ) -> Optional[str]:
        """
        Register new trade

        Args:
            instrument: Instrument
            direction: 'LONG' or 'SHORT'
            size: Position size
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)

        Returns:
            Trade ID or None if rejected
        """
        # Calculate stop loss percentage
        if direction == 'LONG':
            stop_loss_pct = abs(entry_price - stop_loss) / entry_price
        else:
            stop_loss_pct = abs(stop_loss - entry_price) / entry_price

        # Check if can open
        can_trade, reason = self.can_open_trade(instrument, size, stop_loss_pct)

        if not can_trade:
            logger.warning(f"Trade rejected: {reason}")
            return None

        # Create trade record
        trade_id = f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        trade = TradeRecord(
            entry_time=datetime.now(),
            exit_time=None,
            instrument=instrument,
            direction=direction,
            size=size,
            entry_price=entry_price,
            exit_price=None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=None,
            is_winner=None
        )

        self.active_trades[trade_id] = trade

        logger.info(f"Trade opened: {trade_id} - {direction} {instrument} @ {entry_price}")

        return trade_id

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "Manual"
    ) -> Optional[float]:
        """
        Close existing trade

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            reason: Reason for closure

        Returns:
            PnL or None
        """
        if trade_id not in self.active_trades:
            logger.error(f"Trade {trade_id} not found")
            return None

        trade = self.active_trades[trade_id]

        # Calculate PnL
        if trade.direction == 'LONG':
            pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        else:  # SHORT
            pnl_pct = (trade.entry_price - exit_price) / trade.entry_price

        pnl_amount = self.current_balance * trade.size * pnl_pct

        # Update trade record
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.pnl = pnl_amount
        trade.is_winner = pnl_amount > 0

        # Update account
        self.current_balance += pnl_amount
        self.daily_pnl += pnl_amount

        # Update consecutive losses
        if trade.is_winner:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # Move to daily trades
        self.daily_trades.append(trade)
        del self.active_trades[trade_id]

        logger.info(
            f"Trade closed: {trade_id} - {reason} - "
            f"PnL: ${pnl_amount:.2f} ({pnl_pct:.2%})"
        )

        # Check risk status
        self._update_risk_status()

        return pnl_amount

    def check_stop_loss(
        self,
        trade_id: str,
        current_price: float
    ) -> bool:
        """
        Check if stop loss should be triggered

        Args:
            trade_id: Trade ID
            current_price: Current market price

        Returns:
            True if stop loss hit
        """
        if trade_id not in self.active_trades:
            return False

        trade = self.active_trades[trade_id]

        if trade.direction == 'LONG':
            return current_price <= trade.stop_loss
        else:  # SHORT
            return current_price >= trade.stop_loss

    def update_trailing_stop(
        self,
        trade_id: str,
        current_price: float,
        regime_type: RegimeType
    ) -> Optional[float]:
        """
        Update trailing stop for trade

        Args:
            trade_id: Trade ID
            current_price: Current price
            regime_type: Current regime

        Returns:
            New stop loss or None
        """
        if trade_id not in self.active_trades:
            return None

        trade = self.active_trades[trade_id]
        stops_config = self.risk_config.get('stops', {})

        # Get regime-specific config
        if regime_type in [RegimeType.STRONG_RISK_ON, RegimeType.STRONG_RISK_OFF]:
            regime_stops = stops_config.get('strong_regime', {})
        else:
            regime_stops = stops_config.get('weak_regime', {})

        trailing_pct = regime_stops.get('trailing', 0.003)
        activation_pct = regime_stops.get('trailing_activation', 0.005)

        # Check if profitable enough to activate trailing
        if trade.direction == 'LONG':
            profit_pct = (current_price - trade.entry_price) / trade.entry_price
            if profit_pct >= activation_pct:
                new_stop = current_price * (1 - trailing_pct)
                if new_stop > trade.stop_loss:
                    trade.stop_loss = new_stop
                    logger.info(f"Trailing stop updated for {trade_id}: {new_stop:.2f}")
                    return new_stop
        else:  # SHORT
            profit_pct = (trade.entry_price - current_price) / trade.entry_price
            if profit_pct >= activation_pct:
                new_stop = current_price * (1 + trailing_pct)
                if new_stop < trade.stop_loss:
                    trade.stop_loss = new_stop
                    logger.info(f"Trailing stop updated for {trade_id}: {new_stop:.2f}")
                    return new_stop

        return None

    def emergency_flatten_all(self, reason: str = "Emergency") -> None:
        """
        Close all active positions immediately

        Args:
            reason: Reason for emergency flatten
        """
        logger.critical(f"EMERGENCY FLATTEN ALL: {reason}")

        trade_ids = list(self.active_trades.keys())

        for trade_id in trade_ids:
            trade = self.active_trades[trade_id]
            # Close at entry price (conservative assumption in emergency)
            self.close_trade(trade_id, trade.entry_price, reason=f"EMERGENCY: {reason}")

        self.current_status = RiskStatus.LOCKED
        self.locked_until = datetime.now() + timedelta(hours=1)

        logger.critical(f"All positions flattened. Locked until {self.locked_until}")

    def _update_risk_status(self) -> None:
        """Update current risk status based on metrics"""
        daily_dd_pct = self.daily_pnl / self.session_start_balance if self.session_start_balance > 0 else 0

        if self.consecutive_losses >= self.max_consecutive_losses:
            self.current_status = RiskStatus.LOCKED
        elif abs(daily_dd_pct) >= self.max_daily_drawdown:
            self.current_status = RiskStatus.LOCKED
        elif abs(daily_dd_pct) >= self.max_daily_drawdown * 0.7:
            self.current_status = RiskStatus.CRITICAL
        elif abs(daily_dd_pct) >= self.max_daily_drawdown * 0.5:
            self.current_status = RiskStatus.WARNING
        else:
            self.current_status = RiskStatus.NORMAL

    def get_status(self) -> Dict:
        """
        Get comprehensive risk status

        Returns:
            Status dictionary
        """
        daily_dd_pct = self.daily_pnl / self.session_start_balance if self.session_start_balance > 0 else 0

        return {
            'current_status': self.current_status.value,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'current_balance': self.current_balance,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': daily_dd_pct,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            'daily_trades_count': len(self.daily_trades),
            'active_trades_count': len(self.active_trades),
            'remaining_daily_risk': self.max_daily_risk - abs(daily_dd_pct),
            'can_trade': self.current_status != RiskStatus.LOCKED
        }

    def get_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics for current session

        Returns:
            Metrics dictionary
        """
        if not self.daily_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0
            }

        winners = [t for t in self.daily_trades if t.is_winner]
        losers = [t for t in self.daily_trades if not t.is_winner]

        total_wins = sum(t.pnl for t in winners) if winners else 0
        total_losses = sum(abs(t.pnl) for t in losers) if losers else 0

        return {
            'total_trades': len(self.daily_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(self.daily_trades) if self.daily_trades else 0,
            'avg_win': total_wins / len(winners) if winners else 0,
            'avg_loss': total_losses / len(losers) if losers else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'largest_win': max((t.pnl for t in winners), default=0),
            'largest_loss': min((t.pnl for t in losers), default=0)
        }
