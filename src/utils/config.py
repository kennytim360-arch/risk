"""
Configuration Management Module
Handles loading and validation of system configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
import os


class ConfigManager:
    """Manages system configuration from YAML files"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to config file (default: config/settings.yaml)
        """
        if config_path is None:
            self.config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        else:
            self.config_path = Path(config_path)

        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            # Check if config exists, if not use example
            if not self.config_path.exists():
                example_path = self.config_path.parent / "settings.example.yaml"
                if example_path.exists():
                    logger.warning(
                        f"Config not found at {self.config_path}, using example config"
                    )
                    self.config_path = example_path
                else:
                    raise FileNotFoundError(f"No config file found at {self.config_path}")

            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)

            logger.info(f"Configuration loaded from {self.config_path}")
            self._validate_config()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _validate_config(self) -> None:
        """Validate configuration structure and required fields"""
        required_sections = [
            'account',
            'data_feed',
            'instruments',
            'trading_hours',
            'regime',
            'correlation',
            'risk_management'
        ]

        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")

        logger.debug("Configuration validation successful")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key

        Args:
            key: Configuration key (e.g., 'account.max_trade_risk')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_instrument_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific instrument

        Args:
            symbol: Instrument symbol

        Returns:
            Instrument configuration dict or None
        """
        primary = self.config.get('instruments', {}).get('primary', [])
        for inst in primary:
            if inst.get('internal_name') == symbol or inst.get('symbol') == symbol:
                return inst

        return None

    def get_vix_threshold_config(self, vix_level: float) -> Dict[str, Any]:
        """
        Get VIX-adaptive threshold configuration for current VIX level

        Args:
            vix_level: Current VIX value

        Returns:
            Threshold configuration dict
        """
        thresholds = self.config.get('regime', {}).get('vix_thresholds', {})

        if vix_level < 15:
            return thresholds.get('low', {})
        elif vix_level < 20:
            return thresholds.get('normal', {})
        elif vix_level < 25:
            return thresholds.get('elevated', {})
        else:
            return thresholds.get('high', {})

    def get_trading_session(self, current_time: str) -> Optional[Dict[str, Any]]:
        """
        Get current trading session configuration

        Args:
            current_time: Current time in HH:MM format (GMT)

        Returns:
            Session configuration or None
        """
        from datetime import datetime

        current = datetime.strptime(current_time, "%H:%M").time()
        sessions = self.config.get('trading_hours', {})

        for session_name, session_config in sessions.items():
            if session_name == 'flatten_time':
                continue

            start = datetime.strptime(session_config['start'], "%H:%M").time()
            end = datetime.strptime(session_config['end'], "%H:%M").time()

            if start <= current < end:
                return {
                    'name': session_name,
                    **session_config
                }

        return None

    def reload(self) -> None:
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        self.load_config()


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get singleton ConfigManager instance

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
