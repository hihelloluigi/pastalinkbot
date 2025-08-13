"""
Main Bot Class

This module contains the main PAstaLinkBot class that orchestrates all
bot functionality and manages the application lifecycle.

Classes:
    PAstaLinkBot: Main bot application class
"""

import logging
import time
from typing import Optional

from telegram.ext import ApplicationBuilder, ConversationHandler

from config.constants import ConversationState
from config.settings import Settings
from core.handlers.commands import CommandHandlers
from core.handlers.conversation import ConversationHandlers
from core.handlers.messages import MessageHandlers
from core.services.catalog import CatalogService
from core.services.classifier import ClassificationService
from core.services.formatter import ResponseFormatterService
from core.services.validator import InputValidationService
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class PAstaLinkBot(LoggerMixin):
    """
    Main PAstaLinkBot application class.

    This class orchestrates all bot functionality, manages services,
    and handles the application lifecycle.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the bot with configuration settings.

        Args:
            settings: Application configuration settings
        """
        self.settings = settings
        self.application: Optional[ApplicationBuilder] = None

        # Initialize services
        self._initialize_services()

        # Initialize handlers
        self._initialize_handlers()

        self.logger.info("PAstaLinkBot initialized successfully")

    def _initialize_services(self) -> None:
        """Initialize all application services."""
        try:
            # Catalog service
            self.catalog_service = CatalogService(
                data_path=self.settings.data_path,
                max_links_per_response=self.settings.max_links_per_response,
            )

            # Input validation service
            regions = self.catalog_service.get_regions()
            self.validation_service = InputValidationService(
                regions=regions,
                max_message_length=self.settings.max_message_length,
                fuzzy_match_threshold=self.settings.fuzzy_match_threshold,
                suggestion_threshold=self.settings.suggestion_threshold,
            )

            # Classification service
            self.classification_service = ClassificationService(
                cache_size=self.settings.cache_size_classifications
            )

            # Response formatter service
            self.formatter_service = ResponseFormatterService(
                max_links=self.settings.max_links_per_response,
                regions_per_message=self.settings.regions_per_message,
            )

            self.logger.info("All services initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise

    def _initialize_handlers(self) -> None:
        """Initialize all message and command handlers."""
        try:
            # Command handlers
            self.command_handlers = CommandHandlers(
                catalog_service=self.catalog_service,
                validation_service=self.validation_service,
                formatter_service=self.formatter_service,
                admin_user_ids=set(self.settings.admin_user_ids),
            )

            # Message handlers
            self.message_handlers = MessageHandlers(
                catalog_service=self.catalog_service,
                validation_service=self.validation_service,
                classification_service=self.classification_service,
                formatter_service=self.formatter_service,
            )

            # Conversation handlers
            self.conversation_handlers = ConversationHandlers(
                catalog_service=self.catalog_service,
                validation_service=self.validation_service,
                formatter_service=self.formatter_service,
            )

            self.logger.info("All handlers initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize handlers: {e}")
            raise

    def _setup_application(self) -> None:
        """Setup Telegram application with handlers."""
        try:
            # Create application
            self.application = ApplicationBuilder().token(self.settings.telegram_token).build()

            # Add command handlers
            self.application.add_handler(self.command_handlers.start_handler)
            self.application.add_handler(self.command_handlers.help_handler)
            self.application.add_handler(self.command_handlers.about_handler)
            self.application.add_handler(self.command_handlers.stats_handler)
            self.application.add_handler(self.command_handlers.regions_handler)

            # Add conversation handler for region selection
            conversation_handler = ConversationHandler(
                entry_points=[self.message_handlers.message_handler],
                states={
                    ConversationState.ASK_REGION.value: [self.conversation_handlers.region_handler]
                },
                fallbacks=[
                    self.command_handlers.start_handler,
                    self.command_handlers.help_handler,
                ],
                name="region_conversation",
                persistent=False,
            )

            self.application.add_handler(conversation_handler)

            self.logger.info("Telegram application configured successfully")

        except Exception as e:
            self.logger.error(f"Failed to setup application: {e}")
            raise

    def run(self) -> None:
        """
        Start the bot and run until interrupted.

        This method starts the polling loop and handles graceful shutdown.
        """
        try:
            if not self.settings.telegram_token:
                raise ValueError("Telegram token is required")

            # Setup application
            self._setup_application()

            # Log startup information
            self._log_startup_info()

            # Start polling
            self.logger.info("Starting bot polling...")
            self.application.run_polling(
                drop_pending_updates=True,  # Clear pending updates on startup
                close_loop=False,  # Keep event loop running
            )

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise
        finally:
            self._cleanup()

    def _log_startup_info(self) -> None:
        """Log comprehensive startup information."""
        try:
            catalog_stats = self.catalog_service.get_statistics()
            validation_stats = self.validation_service.get_validation_stats()

            self.logger.info("=== PAstaLinkBot Startup Information ===")
            self.logger.info(f"Environment: {self.settings.environment}")
            self.logger.info(f"Log level: {self.settings.log_level}")
            self.logger.info(f"Catalog entries: {catalog_stats['index']['total_entries']}")
            self.logger.info(f"Available intents: {catalog_stats['index']['intents']}")
            self.logger.info(f"Available regions: {catalog_stats['index']['regions']}")
            self.logger.info(f"Admin users: {len(self.settings.admin_user_ids)}")
            self.logger.info(f"Max message length: {self.settings.max_message_length}")
            self.logger.info(f"Max links per response: {self.settings.max_links_per_response}")
            self.logger.info(f"Cache size - Links: {self.settings.cache_size_links}")
            self.logger.info(
                f"Cache size - Classifications: {self.settings.cache_size_classifications}"
            )

            # Log any catalog validation issues
            if self.catalog_service.is_empty:
                self.logger.warning("Catalog is empty - no links will be available")

            validation_report = self.catalog_service.validate_catalog()
            if not validation_report["valid"]:
                self.logger.warning("Catalog validation issues detected:")
                for error in validation_report["errors"]:
                    self.logger.warning(f"  ERROR: {error}")
                for warning in validation_report["warnings"]:
                    self.logger.warning(f"  WARNING: {warning}")

            self.logger.info("=== Bot Ready ===")

        except Exception as e:
            self.logger.error(f"Error logging startup info: {e}")

    def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        try:
            self.logger.info("Cleaning up resources...")

            # Clear caches
            if hasattr(self.catalog_service, "index") and self.catalog_service.index:
                self.catalog_service.index.clear_cache()

            if hasattr(self.classification_service, "clear_cache"):
                self.classification_service.clear_cache()

            self.logger.info("Cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def reload_catalog(self) -> bool:
        """
        Reload catalog from file and update dependent services.

        Returns:
            bool: True if reload was successful, False otherwise
        """
        try:
            self.logger.info("Reloading catalog...")

            # Reload catalog
            success = self.catalog_service.reload_catalog()
            if not success:
                return False

            # Update validation service with new regions
            new_regions = self.catalog_service.get_regions()
            self.validation_service.update_regions(new_regions)

            self.logger.info("Catalog reloaded successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reload catalog: {e}")
            return False

    def get_health_status(self) -> dict:
        """
        Get comprehensive health status of the bot.

        Returns:
            dict: Health status information
        """
        try:
            catalog_stats = self.catalog_service.get_statistics()
            validation_stats = self.validation_service.get_validation_stats()

            health = {
                "status": "healthy",
                "timestamp": None,
                "services": {
                    "catalog": {
                        "status": ("healthy" if not self.catalog_service.is_empty else "warning"),
                        "entries": catalog_stats["index"]["total_entries"],
                        "intents": catalog_stats["index"]["intents"],
                        "regions": catalog_stats["index"]["regions"],
                        "cache_hits": catalog_stats["index"]["cache_hits"],
                        "cache_misses": catalog_stats["index"]["cache_misses"],
                    },
                    "validation": {
                        "status": "healthy",
                        "total_regions": validation_stats["total_regions"],
                        "aliases": validation_stats["aliases"],
                    },
                    "classification": {
                        "status": "healthy",
                        "cache_size": self.settings.cache_size_classifications,
                    },
                    "formatter": {
                        "status": "healthy",
                        "max_links": self.settings.max_links_per_response,
                    },
                },
                "configuration": {
                    "environment": self.settings.environment,
                    "max_message_length": self.settings.max_message_length,
                    "admin_users": len(self.settings.admin_user_ids),
                },
            }

            # Set timestamp
            health["timestamp"] = time.time()

            # Check overall health
            service_statuses = [service["status"] for service in health["services"].values()]
            if "error" in service_statuses:
                health["status"] = "error"
            elif "warning" in service_statuses:
                health["status"] = "warning"

            return health

        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {"status": "error", "error": str(e), "timestamp": time.time()}

    def stop(self) -> None:
        """
        Gracefully stop the bot.

        This method can be called to stop the bot programmatically.
        """
        try:
            if self.application:
                self.logger.info("Stopping bot...")
                self.application.stop()
                self._cleanup()
                self.logger.info("Bot stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")

    @property
    def is_running(self) -> bool:
        """Check if bot is currently running."""
        return self.application is not None and self.application.running

    @property
    def uptime(self) -> Optional[float]:
        """Get bot uptime in seconds (if available)."""
        # This would need to be implemented with a start timestamp
        # For now, return None
        return None
