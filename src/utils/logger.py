"""
Logging Configuration Module
Provides structured logging with rotation and filtering
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(
    log_file: Optional[str] = None,
    level: str = "INFO",
    rotation: str = "1 day",
    retention: str = "30 days"
) -> None:
    """
    Configure loguru logger with file and console output

    Args:
        log_file: Path to log file (default: logs/roro_system.log)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        rotation: When to rotate log files
        retention: How long to keep old logs
    """
    # Remove default handler
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level,
        colorize=True
    )

    # Add file handler with rotation
    if log_file is None:
        log_file = Path(__file__).parent.parent.parent / "logs" / "roro_system.log"
    else:
        log_file = Path(log_file)

    # Create logs directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip"
    )

    logger.info(f"Logger initialized - Level: {level}, File: {log_file}")


def get_logger():
    """Get configured logger instance"""
    return logger
