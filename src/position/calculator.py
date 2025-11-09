"""
Position Sizing Calculator
Implements VIX-adaptive and regime-based position sizing
"""

from dataclasses import dataclass
from typing import Dict, Optional
from loguru import logger

from ..regime.classifier import RegimeType
from ..correlation.analyzer import CorrelationHealth
from ..utils.config import ConfigManager


@dataclass
class PositionSize:
    """Position size calculation result"""
    size: float  # Position size as percentage of account
    contracts: int  # Number of contracts/lots
    risk_amount: float  # Dollar risk amount
    regime_multiplier: float
    vix_multiplier: float
    correlation_multiplier: float
    final_multiplier: float
    regime_type: str
    correlation_health: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'size': self.size,
            'contracts': self.contracts,
            'risk_amount': self.risk_amount,
            'regime_multiplier': self.regime_multiplier,
            'vix_multiplier': self.vix_multiplier,
            'correlation_multiplier': self.correlation_multiplier,
            'final_multiplier': self.final_multiplier,
            'regime_type': self.regime_type,
            'correlation_health': self.correlation_health
        }


class PositionSizeCalculator:
    """Calculate optimal position sizes based on multiple factors"""

    def __init__(self, config: ConfigManager):
        """
        Initialize position size calculator

        Args:
            config: Configuration manager
        """
        self.config = config
        self.sizing_config = config.get('position_sizing', {})
        self.account_config = config.get('account', {})

        # Base parameters
        self.base_risk = self.sizing_config.get('base_risk', 0.02)  # 2%
        self.max_position_risk = self.sizing_config.get('max_position_risk', 0.02)

        # Regime multipliers
        self.regime_multipliers = self.sizing_config.get('regime_multipliers', {
            'strong': 1.0,
            'weak': 0.5,
            'transition': 0.25,
            'divergence': 0.5
        })

        # VIX adjustment
        self.vix_enabled = self.sizing_config.get('vix_adjustment', {}).get('enabled', True)
        self.base_vix = self.sizing_config.get('vix_adjustment', {}).get('base_vix', 20)
        self.max_vix_multiplier = self.sizing_config.get('vix_adjustment', {}).get('max_multiplier', 1.5)

    def get_regime_multiplier(self, regime_type: RegimeType) -> float:
        """
        Get position size multiplier for regime type

        Args:
            regime_type: Current regime

        Returns:
            Multiplier value
        """
        if regime_type == RegimeType.STRONG_RISK_ON or regime_type == RegimeType.STRONG_RISK_OFF:
            return self.regime_multipliers.get('strong', 1.0)
        elif regime_type == RegimeType.WEAK_RISK_ON or regime_type == RegimeType.WEAK_RISK_OFF:
            return self.regime_multipliers.get('weak', 0.5)
        elif regime_type == RegimeType.TRANSITION:
            return self.regime_multipliers.get('transition', 0.25)
        else:
            return 0.25

    def get_vix_multiplier(self, vix_level: float) -> float:
        """
        Get VIX-adjusted multiplier

        Args:
            vix_level: Current VIX value

        Returns:
            Multiplier value
        """
        if not self.vix_enabled:
            return 1.0

        # Lower VIX = higher position size (inverse relationship)
        # Formula: min(base_vix / current_vix, max_multiplier)
        if vix_level <= 0:
            return 1.0

        multiplier = self.base_vix / vix_level
        return min(multiplier, self.max_vix_multiplier)

    def get_correlation_multiplier(self, correlation_health: CorrelationHealth) -> float:
        """
        Get correlation-based multiplier

        Args:
            correlation_health: Current correlation health

        Returns:
            Multiplier value
        """
        if correlation_health == CorrelationHealth.HEALTHY:
            return 1.0
        elif correlation_health == CorrelationHealth.DEGRADED:
            return 0.5
        else:  # BROKEN
            return 0.0

    def calculate_position_size(
        self,
        account_balance: float,
        regime_type: RegimeType,
        vix_level: float,
        correlation_health: CorrelationHealth,
        is_divergence_trade: bool = False,
        stop_loss_percent: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate optimal position size

        Args:
            account_balance: Current account balance
            regime_type: Current market regime
            vix_level: Current VIX level
            correlation_health: Current correlation health
            is_divergence_trade: Whether this is a divergence trade
            stop_loss_percent: Stop loss percentage (optional)

        Returns:
            PositionSize object
        """
        # Get multipliers
        if is_divergence_trade:
            regime_mult = self.regime_multipliers.get('divergence', 0.5)
        else:
            regime_mult = self.get_regime_multiplier(regime_type)

        vix_mult = self.get_vix_multiplier(vix_level)
        corr_mult = self.get_correlation_multiplier(correlation_health)

        # Calculate final multiplier
        final_mult = regime_mult * vix_mult * corr_mult

        # Calculate base position size
        base_size = self.base_risk * final_mult

        # Cap at maximum
        position_size = min(base_size, self.max_position_risk)

        # Calculate risk amount
        risk_amount = account_balance * position_size

        # Calculate contracts (simplified - would need instrument details)
        # For now, assume each contract = $50,000 exposure
        contract_value = 50000
        if stop_loss_percent:
            # Adjust for stop loss
            risk_per_contract = contract_value * stop_loss_percent
            contracts = int(risk_amount / risk_per_contract) if risk_per_contract > 0 else 0
        else:
            # Default: 1 contract per $50k risk
            contracts = max(1, int(risk_amount / contract_value))

        logger.debug(
            f"Position size calculated: {position_size:.4f} "
            f"(Regime: {regime_mult}, VIX: {vix_mult:.2f}, Corr: {corr_mult})"
        )

        return PositionSize(
            size=position_size,
            contracts=contracts,
            risk_amount=risk_amount,
            regime_multiplier=regime_mult,
            vix_multiplier=vix_mult,
            correlation_multiplier=corr_mult,
            final_multiplier=final_mult,
            regime_type=regime_type.value,
            correlation_health=correlation_health.value
        )

    def calculate_for_divergence(
        self,
        account_balance: float,
        vix_level: float,
        correlation_health: CorrelationHealth,
        stop_loss_percent: float = 0.0025  # 0.25% default for divergence
    ) -> PositionSize:
        """
        Calculate position size specifically for divergence trades

        Args:
            account_balance: Current account balance
            vix_level: Current VIX level
            correlation_health: Current correlation health
            stop_loss_percent: Stop loss percentage

        Returns:
            PositionSize object
        """
        # Divergence trades always use reduced size (counter-trend)
        return self.calculate_position_size(
            account_balance=account_balance,
            regime_type=RegimeType.TRANSITION,  # Use transition as proxy
            vix_level=vix_level,
            correlation_health=correlation_health,
            is_divergence_trade=True,
            stop_loss_percent=stop_loss_percent
        )

    def should_reduce_size(
        self,
        current_time: str,
        session_config: Optional[Dict] = None
    ) -> float:
        """
        Check if size should be reduced based on time/session

        Args:
            current_time: Current time in HH:MM format
            session_config: Session configuration

        Returns:
            Size multiplier (0.0 to 1.0)
        """
        if session_config is None:
            session_config = self.config.get_trading_session(current_time)

        if session_config is None:
            return 0.0  # Outside trading hours

        # Check for size reduction within session
        if 'reduce_time' in session_config:
            from datetime import datetime
            current = datetime.strptime(current_time, "%H:%M").time()
            reduce = datetime.strptime(session_config['reduce_time'], "%H:%M").time()

            if current >= reduce:
                return session_config.get('reduce_multiplier', 0.5)

        return session_config.get('max_size_multiplier', 1.0)

    def get_recommended_stop_loss(
        self,
        regime_type: RegimeType,
        is_divergence: bool = False
    ) -> float:
        """
        Get recommended stop loss percentage for regime

        Args:
            regime_type: Current regime
            is_divergence: Whether divergence trade

        Returns:
            Stop loss percentage
        """
        stops_config = self.config.get('risk_management', {}).get('stops', {})

        if is_divergence:
            return stops_config.get('divergence', {}).get('initial', 0.0025)

        if regime_type in [RegimeType.STRONG_RISK_ON, RegimeType.STRONG_RISK_OFF]:
            return stops_config.get('strong_regime', {}).get('initial', 0.005)
        else:
            return stops_config.get('weak_regime', {}).get('initial', 0.003)
