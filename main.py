#!/usr/bin/env python3
"""
PAstaLinkBot - Main Entry Point

This is the main entry point for the PAstaLinkBot Telegram application.
It initializes the configuration, sets up logging, and starts the bot.

Usage:
    python main.py

Author: Luigi Aiello
License: MIT
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings, load_settings
from core.bot import PAstaLinkBot
from utils.logging import setup_logging


def main() -> None:
    """
    Main application entry point.

    Initializes configuration, logging, and starts the Telegram bot.
    Handles graceful shutdown on interruption.

    Raises:
        SystemExit: If required configuration is missing or bot fails to start
    """
    try:
        # Load configuration
        settings = load_settings()

        # Setup logging
        logger = setup_logging(settings.log_level, settings.environment)
        logger.info("Starting PAstaLinkBot...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Log level: {settings.log_level}")

        # Validate required configuration
        if not settings.telegram_token:
            logger.error("TELEGRAM_TOKEN environment variable is required")
            sys.exit(1)

        # Initialize and start bot
        bot = PAstaLinkBot(settings)

        logger.info("Bot initialization complete. Starting polling...")
        bot.run()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
