"""
Tests for Position Size Calculator
"""

import pytest
from src.position.calculator import PositionSizeCalculator
from src.regime.classifier import RegimeType
from src.correlation.analyzer import CorrelationHealth
from src.utils.config import ConfigManager


@pytest.fixture
def config():
    """Create test configuration"""
    return ConfigManager()


@pytest.fixture
def calculator(config):
    """Create position calculator instance"""
    return PositionSizeCalculator(config)


class TestPositionSizeCalculator:
    """Test PositionSizeCalculator functionality"""

    def test_initialization(self, calculator):
        """Test calculator initializes correctly"""
        assert calculator is not None
        assert calculator.base_risk == 0.02
        assert calculator.max_position_risk == 0.02

    def test_regime_multiplier_strong(self, calculator):
        """Test regime multiplier for strong regime"""
        mult = calculator.get_regime_multiplier(RegimeType.STRONG_RISK_ON)
        assert mult == 1.0

    def test_regime_multiplier_weak(self, calculator):
        """Test regime multiplier for weak regime"""
        mult = calculator.get_regime_multiplier(RegimeType.WEAK_RISK_ON)
        assert mult == 0.5

    def test_regime_multiplier_transition(self, calculator):
        """Test regime multiplier for transition"""
        mult = calculator.get_regime_multiplier(RegimeType.TRANSITION)
        assert mult == 0.25

    def test_vix_multiplier_low(self, calculator):
        """Test VIX multiplier for low VIX"""
        mult = calculator.get_vix_multiplier(15.0)
        assert mult > 1.0  # Lower VIX = higher size

    def test_vix_multiplier_high(self, calculator):
        """Test VIX multiplier for high VIX"""
        mult = calculator.get_vix_multiplier(25.0)
        assert mult < 1.0  # Higher VIX = lower size

    def test_vix_multiplier_capped(self, calculator):
        """Test VIX multiplier is capped at maximum"""
        mult = calculator.get_vix_multiplier(5.0)  # Very low VIX
        assert mult <= calculator.max_vix_multiplier

    def test_correlation_multiplier(self, calculator):
        """Test correlation-based multipliers"""
        assert calculator.get_correlation_multiplier(CorrelationHealth.HEALTHY) == 1.0
        assert calculator.get_correlation_multiplier(CorrelationHealth.DEGRADED) == 0.5
        assert calculator.get_correlation_multiplier(CorrelationHealth.BROKEN) == 0.0

    def test_position_size_calculation(self, calculator):
        """Test full position size calculation"""
        account_balance = 100000.0

        pos_size = calculator.calculate_position_size(
            account_balance=account_balance,
            regime_type=RegimeType.STRONG_RISK_ON,
            vix_level=18.0,
            correlation_health=CorrelationHealth.HEALTHY
        )

        assert pos_size is not None
        assert pos_size.size > 0
        assert pos_size.size <= calculator.max_position_risk
        assert pos_size.risk_amount == account_balance * pos_size.size
        assert pos_size.contracts > 0

    def test_divergence_position_sizing(self, calculator):
        """Test position sizing for divergence trades"""
        account_balance = 100000.0

        pos_size = calculator.calculate_for_divergence(
            account_balance=account_balance,
            vix_level=20.0,
            correlation_health=CorrelationHealth.HEALTHY
        )

        # Divergence trades should have reduced size
        assert pos_size.size < 0.02
        assert pos_size.regime_multiplier == 0.5  # Divergence penalty

    def test_broken_correlation_zero_size(self, calculator):
        """Test that broken correlation results in zero position size"""
        pos_size = calculator.calculate_position_size(
            account_balance=100000.0,
            regime_type=RegimeType.STRONG_RISK_ON,
            vix_level=18.0,
            correlation_health=CorrelationHealth.BROKEN
        )

        assert pos_size.size == 0.0
        assert pos_size.correlation_multiplier == 0.0

    def test_recommended_stop_loss(self, calculator):
        """Test recommended stop loss calculation"""
        # Strong regime
        stop = calculator.get_recommended_stop_loss(RegimeType.STRONG_RISK_ON)
        assert stop == 0.005  # 0.5%

        # Weak regime
        stop = calculator.get_recommended_stop_loss(RegimeType.WEAK_RISK_ON)
        assert stop == 0.003  # 0.3%

        # Divergence
        stop = calculator.get_recommended_stop_loss(
            RegimeType.STRONG_RISK_ON,
            is_divergence=True
        )
        assert stop == 0.0025  # 0.25%


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
