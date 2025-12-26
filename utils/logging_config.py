"""Structured logging configuration for Codey Engine

Provides centralized logging configuration with:
- Support for log levels (DEBUG, INFO, WARNING, ERROR)
- File logging with rotation
- Optional console output
- Timestamps, module names, and context
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Default log directory
DEFAULT_LOG_DIR = Path.home() / ".codey" / "logs"

# Log format with timestamp, level, module, and message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_FORMAT_DETAILED = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Console format (more compact)
CONSOLE_FORMAT = "%(levelname)-8s | %(message)s"


class CodeyLogger:
    """Centralized logging configuration for Codey"""

    _instance: Optional['CodeyLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if CodeyLogger._initialized:
            return
        CodeyLogger._initialized = True

        self.log_dir = DEFAULT_LOG_DIR
        self.log_level = logging.INFO
        self.console_enabled = True
        self.file_enabled = True
        self._root_logger = logging.getLogger("codey")
        self._configured = False

    def configure(
        self,
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
        console_enabled: bool = True,
        file_enabled: bool = True,
        detailed_format: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """Configure the logging system

        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            console_enabled: Whether to output to console
            file_enabled: Whether to log to file
            detailed_format: Use detailed format with function names and line numbers
            max_bytes: Max size of each log file before rotation
            backup_count: Number of backup files to keep
        """
        if self._configured:
            # Already configured, just update level
            self._root_logger.setLevel(log_level)
            return

        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.log_level = log_level
        self.console_enabled = console_enabled
        self.file_enabled = file_enabled

        # Set root logger level
        self._root_logger.setLevel(log_level)

        # Choose format
        log_format = LOG_FORMAT_DETAILED if detailed_format else LOG_FORMAT

        # Add console handler
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
            self._root_logger.addHandler(console_handler)

        # Add file handler with rotation
        if file_enabled:
            self._setup_file_handler(log_format, max_bytes, backup_count)

        self._configured = True

    def _setup_file_handler(
        self,
        log_format: str,
        max_bytes: int,
        backup_count: int
    ) -> None:
        """Setup rotating file handler"""
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file path with date
        log_file = self.log_dir / f"codey_{datetime.now().strftime('%Y%m%d')}.log"

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(logging.Formatter(log_format, DATE_FORMAT))
        self._root_logger.addHandler(file_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific module

        Args:
            name: Module name (e.g., "orchestrator", "router")

        Returns:
            Logger instance for the module
        """
        return logging.getLogger(f"codey.{name}")

    def set_level(self, level: int) -> None:
        """Set log level for all loggers

        Args:
            level: Logging level
        """
        self._root_logger.setLevel(level)
        for handler in self._root_logger.handlers:
            handler.setLevel(level)


# Global instance
_codey_logger = CodeyLogger()


def configure_logging(
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    console_enabled: bool = True,
    file_enabled: bool = True,
    detailed_format: bool = False
) -> None:
    """Configure the Codey logging system

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        console_enabled: Whether to output to console
        file_enabled: Whether to log to file
        detailed_format: Use detailed format with function names and line numbers
    """
    _codey_logger.configure(
        log_dir=log_dir,
        log_level=log_level,
        console_enabled=console_enabled,
        file_enabled=file_enabled,
        detailed_format=detailed_format
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module

    Args:
        name: Module name (e.g., "orchestrator", "router")

    Returns:
        Logger instance for the module
    """
    return _codey_logger.get_logger(name)


def set_level(level: int) -> None:
    """Set log level for all loggers

    Args:
        level: Logging level (e.g., logging.DEBUG)
    """
    _codey_logger.set_level(level)


# Convenience functions for common log levels
def set_debug() -> None:
    """Set log level to DEBUG"""
    set_level(logging.DEBUG)


def set_info() -> None:
    """Set log level to INFO"""
    set_level(logging.INFO)


def set_warning() -> None:
    """Set log level to WARNING"""
    set_level(logging.WARNING)


def set_error() -> None:
    """Set log level to ERROR"""
    set_level(logging.ERROR)


# Initialize with sensible defaults (no file logging by default for safety)
def init_default_logging() -> None:
    """Initialize logging with safe defaults

    - Console output enabled
    - File logging disabled (to avoid writing to disk unexpectedly)
    - INFO level
    """
    configure_logging(
        console_enabled=False,  # Disable by default to avoid cluttering output
        file_enabled=False,
        log_level=logging.INFO
    )


# Auto-initialize on import
init_default_logging()
