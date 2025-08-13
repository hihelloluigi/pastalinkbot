"""
Configuration Management Module

This module handles all application configuration including environment variables,
default values, and configuration validation.

Classes:
    Settings: Main configuration dataclass

Functions:
    load_settings: Load and validate configuration from environment
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """
    Application configuration settings.

    This dataclass contains all configuration parameters for the bot,
    with sensible defaults and validation.

    Attributes:
        telegram_token: Telegram bot token from @BotFather
        data_path: Path to catalog JSON file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        environment: Runtime environment (development, staging, production)
        max_message_length: Maximum allowed message length from users
        max_links_per_response: Maximum number of links to show in one response
        cache_size_links: LRU cache size for link lookups
        cache_size_classifications: LRU cache size for LLM classifications
        admin_user_ids: List of Telegram user IDs with admin privileges
        fuzzy_match_threshold: Minimum similarity for fuzzy region matching
        suggestion_threshold: Minimum similarity for region suggestions
        regions_per_message: Number of regions to show per message in /regions
    """

    # Required settings
    telegram_token: str = ""

    # Path settings
    data_path: str = "./data/pa_bot_links_seed.json"

    # Runtime settings
    log_level: str = "INFO"
    environment: str = "development"

    # Bot behavior settings
    max_message_length: int = 1000
    max_links_per_response: int = 6

    # Cache settings
    cache_size_links: int = 500
    cache_size_classifications: int = 1000

    # Admin settings
    admin_user_ids: List[int] = field(default_factory=list)

    # Input validation settings
    fuzzy_match_threshold: float = 0.7
    suggestion_threshold: float = 0.4
    regions_per_message: int = 15

    def __post_init__(self):
        """
        Validate configuration after initialization.

        Raises:
            ValueError: If configuration values are invalid
        """
        self._validate_log_level()
        self._validate_environment()
        self._validate_paths()
        self._validate_numeric_settings()

    def _validate_log_level(self) -> None:
        """Validate log level setting."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Must be one of {valid_levels}")
        self.log_level = self.log_level.upper()

    def _validate_environment(self) -> None:
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if self.environment.lower() not in valid_environments:
            raise ValueError(
                f"Invalid environment: {self.environment}. Must be one of {valid_environments}"
            )
        self.environment = self.environment.lower()

    def _validate_paths(self) -> None:
        """Validate file paths."""
        if self.data_path:
            data_file = Path(self.data_path)
            if not data_file.exists():
                logger.warning(f"Data file does not exist: {self.data_path}")

    def _validate_numeric_settings(self) -> None:
        """Validate numeric configuration values."""
        if self.max_message_length <= 0:
            raise ValueError("max_message_length must be positive")

        if self.max_links_per_response <= 0:
            raise ValueError("max_links_per_response must be positive")

        if self.cache_size_links <= 0:
            raise ValueError("cache_size_links must be positive")

        if self.cache_size_classifications <= 0:
            raise ValueError("cache_size_classifications must be positive")

        if not 0.0 <= self.fuzzy_match_threshold <= 1.0:
            raise ValueError("fuzzy_match_threshold must be between 0.0 and 1.0")

        if not 0.0 <= self.suggestion_threshold <= 1.0:
            raise ValueError("suggestion_threshold must be between 0.0 and 1.0")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


def load_settings() -> Settings:
    """
    Load configuration settings from environment variables.

    Reads configuration from environment variables and creates a Settings
    instance with appropriate defaults and validation.

    Returns:
        Settings: Configured settings instance

    Raises:
        ValueError: If configuration validation fails
    """
    logger.info("Loading configuration from environment")

    # Parse admin user IDs from comma-separated string
    admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
    admin_user_ids = []
    if admin_ids_str:
        try:
            admin_user_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
        except ValueError as e:
            logger.warning(f"Invalid admin user IDs format: {admin_ids_str}. Error: {e}")

    settings = Settings(
        telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
        data_path=os.getenv("DATA_PATH", "./data/pa_bot_links_seed.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        environment=os.getenv("ENVIRONMENT", "development"),
        max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "1000")),
        max_links_per_response=int(os.getenv("MAX_LINKS_PER_RESPONSE", "6")),
        cache_size_links=int(os.getenv("CACHE_SIZE_LINKS", "500")),
        cache_size_classifications=int(os.getenv("CACHE_SIZE_CLASSIFICATIONS", "1000")),
        admin_user_ids=admin_user_ids,
        fuzzy_match_threshold=float(os.getenv("FUZZY_MATCH_THRESHOLD", "0.7")),
        suggestion_threshold=float(os.getenv("SUGGESTION_THRESHOLD", "0.4")),
        regions_per_message=int(os.getenv("REGIONS_PER_MESSAGE", "15")),
    )

    logger.info("Configuration loaded successfully")
    logger.debug(f"Data path: {settings.data_path}")
    logger.debug(f"Admin users: {len(settings.admin_user_ids)}")
    logger.debug(
        f"Cache sizes - Links: {settings.cache_size_links}, Classifications: {settings.cache_size_classifications}"
    )

    return settings
