"""
Command Handlers

This module contains handlers for all bot commands (/start, /help, /about, etc.).
Each command has its own handler with proper error handling and logging.

Classes:
    CommandHandlers: Main class containing all command handlers
"""

import logging
from typing import Set

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from core.services.catalog import CatalogService
from core.services.formatter import ResponseFormatterService
from core.services.validator import InputValidationService
from utils.decorators import (
    handle_telegram_errors,
    log_handler_call,
    require_admin,
    validate_update,
)
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class CommandHandlers(LoggerMixin):
    """
    Handler class for all bot commands.

    This class contains handlers for all slash commands like /start, /help, etc.
    Each handler is properly decorated with error handling and logging.
    """

    def __init__(
        self,
        catalog_service: CatalogService,
        validation_service: InputValidationService,
        formatter_service: ResponseFormatterService,
        admin_user_ids: Set[int],
    ):
        """
        Initialize command handlers.

        Args:
            catalog_service: Service for catalog operations
            validation_service: Service for input validation
            formatter_service: Service for response formatting
            admin_user_ids: Set of admin user IDs
        """
        self.catalog_service = catalog_service
        self.validation_service = validation_service
        self.formatter_service = formatter_service
        self.admin_user_ids = admin_user_ids

        # Create handler instances with decorated wrappers
        self.start_handler = CommandHandler("start", self._create_start_wrapper())
        self.help_handler = CommandHandler("help", self._create_help_wrapper())
        self.about_handler = CommandHandler("about", self._create_about_wrapper())
        self.stats_handler = CommandHandler("stats", self._create_stats_wrapper())
        self.regions_handler = CommandHandler("regions", self._create_regions_wrapper())

    def _create_start_wrapper(self):
        """Create decorated wrapper for start command."""

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            return await self._start_command(update, context)

        return wrapper

    def _create_help_wrapper(self):
        """Create decorated wrapper for help command."""

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            return await self._help_command(update, context)

        return wrapper

    def _create_about_wrapper(self):
        """Create decorated wrapper for about command."""

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            return await self._about_command(update, context)

        return wrapper

    def _create_stats_wrapper(self):
        """Create decorated wrapper for stats command."""

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        @require_admin(admin_user_ids=lambda self: self.admin_user_ids)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            return await self._stats_command(update, context)

        return wrapper

    def _create_regions_wrapper(self):
        """Create decorated wrapper for regions command."""

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            return await self._regions_command(update, context)

        return wrapper

        self.logger.info("Command handlers initialized")

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command.

        Shows welcome message and basic help information.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        # Format help response (start and help show the same content)
        response = self.formatter_service.format_help_response(user_language)

        # Send response
        parse_mode = self.formatter_service.get_parse_mode(response)
        await update.message.reply_text(response, parse_mode=parse_mode)

        self.logger.info(f"Start command handled for user {update.effective_user.id}")

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command.

        Shows detailed help information about bot capabilities.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        # Format help response
        response = self.formatter_service.format_help_response(user_language)

        # Send response
        parse_mode = self.formatter_service.get_parse_mode(response)
        await update.message.reply_text(response, parse_mode=parse_mode)

        self.logger.info(f"Help command handled for user {update.effective_user.id}")

    async def _about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /about command.

        Shows information about the bot and its creators.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        # Format about response
        response = self.formatter_service.format_about_response(user_language)

        # Send response
        parse_mode = self.formatter_service.get_parse_mode(response)
        await update.message.reply_text(response, parse_mode=parse_mode)

        self.logger.info(f"About command handled for user {update.effective_user.id}")

    async def _stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /stats command (admin only).

        Shows bot statistics including cache performance and catalog info.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        try:
            # Gather statistics from all services
            catalog_stats = self.catalog_service.get_statistics()
            validation_stats = self.validation_service.get_validation_stats()

            # Combine stats data
            stats_data = {
                "index": catalog_stats.get("index", {}),
                "cache": catalog_stats.get("index", {}),  # Cache stats are in index
                "validator": validation_stats,
            }

            # Format response
            response = self.formatter_service.format_stats_response(stats_data, user_language)

            # Send response
            parse_mode = self.formatter_service.get_parse_mode(response)
            await update.message.reply_text(response, parse_mode=parse_mode)

            self.logger.info(f"Stats command handled for admin user {update.effective_user.id}")

        except Exception as e:
            self.logger.error(f"Error gathering statistics: {e}")
            error_response = self.formatter_service.format_error_response("generic", user_language)
            await update.message.reply_text(error_response)

    async def _regions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /regions command.

        Shows list of all available regions.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        try:
            # Get regions from catalog service
            regions = self.catalog_service.get_regions()

            # Format response
            response = self.formatter_service.format_regions_list(regions, user_language)

            # Send response
            parse_mode = self.formatter_service.get_parse_mode(response)
            await update.message.reply_text(response, parse_mode=parse_mode)

            self.logger.info(
                f"Regions command handled for user {update.effective_user.id}. "
                f"Showed {len(regions)} regions."
            )

        except Exception as e:
            self.logger.error(f"Error getting regions: {e}")
            error_response = self.formatter_service.format_error_response("generic", user_language)
            await update.message.reply_text(error_response)

    def get_all_handlers(self) -> list:
        """
        Get list of all command handlers.

        Returns:
            list: List of CommandHandler instances
        """
        return [
            self.start_handler,
            self.help_handler,
            self.about_handler,
            self.stats_handler,
            self.regions_handler,
        ]

    def get_admin_commands(self) -> list:
        """
        Get list of admin-only commands.

        Returns:
            list: List of admin command names
        """
        return ["stats"]

    def get_public_commands(self) -> list:
        """
        Get list of public commands.

        Returns:
            list: List of public command names
        """
        return ["start", "help", "about", "regions"]
