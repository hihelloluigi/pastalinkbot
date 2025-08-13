"""
Logging Configuration Module

This module provides centralized logging configuration for the application.
It sets up structured logging with appropriate formatters and handlers
based on the environment.

Functions:
    setup_logging: Configure application logging
    get_logger: Get a configured logger for a module
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    environment: str = "development",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application logging with appropriate formatters and handlers.

    Sets up console logging with colored output for development and
    structured logging for production environments.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Runtime environment (development, staging, production)
        log_file: Optional log file path for file output

    Returns:
        logging.Logger: Configured root logger

    Raises:
        ValueError: If log_level is invalid
    """
    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set log level
    root_logger.setLevel(numeric_level)

    # Create formatters
    if environment == "production":
        # Structured format for production
        formatter = logging.Formatter(
            fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s", '
            '"function": "%(funcName)s", "line": %(lineno)d}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)

            root_logger.info(f"File logging enabled: {log_file}")
        except Exception as e:
            root_logger.warning(f"Failed to setup file logging: {e}")

    # Configure third-party loggers
    _configure_third_party_loggers(environment)

    # Log configuration
    root_logger.info(f"Logging configured - Level: {log_level}, Environment: {environment}")

    return root_logger


def _configure_third_party_loggers(environment: str) -> None:
    """
    Configure third-party library loggers to reduce noise.

    Args:
        environment: Runtime environment
    """
    # Reduce httpx/telegram logging verbosity in production
    if environment == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    else:
        # In development, show more details but not debug
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("telegram").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a specific module.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.

    Usage:
        class MyClass(LoggerMixin):
            def some_method(self):
                self.logger.info("Something happened")
    """

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


# Custom logging decorator
def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function calls with arguments and return values.

    Args:
        logger: Optional logger instance. If None, uses module logger.

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            func_name = f"{func.__module__}.{func.__qualname__}"

            # Log function entry
            func_logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")

            try:
                result = func(*args, **kwargs)
                func_logger.debug(f"{func_name} returned: {result}")
                return result
            except Exception as e:
                func_logger.error(f"{func_name} raised {type(e).__name__}: {e}")
                raise

        return wrapper

    return decorator


# Performance logging context manager
import time
from contextlib import contextmanager


@contextmanager
def log_performance(operation_name: str, logger: Optional[logging.Logger] = None):
    """
    Context manager to log performance of operations.

    Args:
        operation_name: Name of the operation being timed
        logger: Optional logger instance

    Usage:
        with log_performance("database_query", logger):
            # ... perform operation
            pass
    """
    perf_logger = logger or logging.getLogger("performance")
    start_time = time.time()

    perf_logger.debug(f"Starting {operation_name}")

    try:
        yield
    finally:
        duration = time.time() - start_time
        perf_logger.info(f"{operation_name} completed in {duration:.3f}s")
