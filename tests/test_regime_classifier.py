"""
Tests for Regime Classifier
"""

import pytest
from datetime import datetime
from src.regime.classifier import RegimeClassifier, RegimeType
from src.data_feeds.base import MarketData
from src.utils.config import ConfigManager


@pytest.fixture
def config():
    """Create test configuration"""
    return ConfigManager()


@pytest.fixture
def classifier(config):
    """Create regime classifier instance"""
    return RegimeClassifier(config)


@pytest.fixture
def sample_market_data():
    """Create sample market data"""
    return {
        'US500': MarketData(
            symbol='US500',
            timestamp=datetime.now(),
            open=4500.0,
            high=4520.0,
            low=4495.0,
            close=4515.0,
            volume=1000000,
            vwap=4510.0
        ),
        'USDJPY': MarketData(
            symbol='USDJPY',
            timestamp=datetime.now(),
            open=150.0,
            high=150.5,
            low=149.8,
            close=150.3,
            volume=500000
        ),
        'VIX': MarketData(
            symbol='VIX',
            timestamp=datetime.now(),
            open=18.0,
            high=18.5,
            low=17.8,
            close=17.9,
            volume=100000
        )
    }


class TestRegimeClassifier:
    """Test RegimeClassifier functionality"""

    def test_initialization(self, classifier):
        """Test classifier initializes correctly"""
        assert classifier is not None
        assert classifier.current_regime is None
        assert len(classifier.price_history) == 5

    def test_vix_thresholds_low(self, classifier):
        """Test VIX threshold calculation for low VIX"""
        thresholds = classifier.get_vix_thresholds(12.0)
        assert thresholds['multiplier'] == 0.7
        assert thresholds['strong_move'] == 0.0035

    def test_vix_thresholds_normal(self, classifier):
        """Test VIX threshold calculation for normal VIX"""
        thresholds = classifier.get_vix_thresholds(17.0)
        assert thresholds['multiplier'] == 1.0
        assert thresholds['strong_move'] == 0.0050

    def test_vix_thresholds_high(self, classifier):
        """Test VIX threshold calculation for high VIX"""
        thresholds = classifier.get_vix_thresholds(30.0)
        assert thresholds['multiplier'] == 1.5
        assert thresholds['strong_move'] == 0.0075

    def test_price_history_update(self, classifier, sample_market_data):
        """Test price history updates correctly"""
        for instrument, data in sample_market_data.items():
            classifier.update_price_history(instrument, data.close, data.timestamp)

        assert len(classifier.price_history['US500']) == 1
        assert len(classifier.price_history['USDJPY']) == 1
        assert len(classifier.price_history['VIX']) == 1

    def test_regime_classification(self, classifier, sample_market_data):
        """Test basic regime classification"""
        # Add some price history first
        for _ in range(10):
            for instrument, data in sample_market_data.items():
                classifier.update_price_history(
                    instrument,
                    data.close,
                    datetime.now()
                )

        regime = classifier.classify_regime(sample_market_data)

        assert regime is not None
        assert isinstance(regime.regime_type, RegimeType)
        assert 0 <= regime.confidence <= 1.0
        assert regime.vix_level > 0

    def test_trading_bias_strong_risk_on(self, classifier):
        """Test trading bias for strong risk-on"""
        # Manually set a strong risk-on regime
        from src.regime.classifier import RegimeClassification

        classifier.current_regime = RegimeClassification(
            regime_type=RegimeType.STRONG_RISK_ON,
            confidence=0.8,
            signals=[],
            timestamp=datetime.now(),
            vix_level=15.0,
            vix_multiplier=0.7
        )

        bias = classifier.get_regime_trading_bias()

        assert bias['action'] == 'LONG'
        assert 'US500' in bias['primary_instruments']
        assert bias['size_multiplier'] == 1.0

    def test_trading_bias_transition(self, classifier):
        """Test trading bias for transition zone"""
        from src.regime.classifier import RegimeClassification

        classifier.current_regime = RegimeClassification(
            regime_type=RegimeType.TRANSITION,
            confidence=0.3,
            signals=[],
            timestamp=datetime.now(),
            vix_level=20.0,
            vix_multiplier=1.0
        )

        bias = classifier.get_regime_trading_bias()

        assert bias['action'] == 'NO_NEW_POSITIONS'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
