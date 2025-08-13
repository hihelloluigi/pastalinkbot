"""
Conversation Handlers

This module contains handlers for multi-step conversations, particularly
for handling region selection when additional information is needed.

Classes:
    ConversationHandlers: Main class for conversation flow management
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from config.constants import ConversationState
from core.models.intent import ClassificationResult, IntentRequest
from core.services.catalog import CatalogService
from core.services.formatter import ResponseFormatterService
from core.services.validator import InputValidationService
from utils.decorators import handle_telegram_errors, log_handler_call, validate_update
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class ConversationHandlers(LoggerMixin):
    """
    Handler class for managing conversation flows.

    This class handles multi-step conversations, particularly when the bot
    needs to ask for additional information like region selection.
    """

    def __init__(
        self,
        catalog_service: CatalogService,
        validation_service: InputValidationService,
        formatter_service: ResponseFormatterService,
    ):
        """
        Initialize conversation handlers.

        Args:
            catalog_service: Service for catalog operations
            validation_service: Service for input validation
            formatter_service: Service for response formatting
        """
        self.catalog_service = catalog_service
        self.validation_service = validation_service
        self.formatter_service = formatter_service

        # Create handler instance for region selection with decorated wrapper
        self.region_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._create_region_handler_wrapper()
        )

    def _create_region_handler_wrapper(self):
        """
        Create a standalone wrapper function with decorators for region selection.

        This creates a function that can be called by Telegram without 'self'.
        """

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
            """
            Standalone wrapper function for handle_region_selection with decorators.
            """
            return await self.handle_region_selection(update, context)

        return wrapper

        self.logger.info("Conversation handlers initialized")

    async def _send_links_response(
        self, intent: str, region: Optional[str], update: Update
    ) -> None:
        """
        Send links response for the given intent and region.

        Args:
            intent: Intent to get links for
            region: Region to filter by
            update: Telegram update object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        try:
            # Get links from catalog
            links = self.catalog_service.get_links(intent, region)

            if links:
                # Format and send links
                response = self.formatter_service.format_links_response(
                    links, intent, user_language
                )
                await update.message.reply_text(response)

                self.logger.info(
                    f"Sent {len(links)} links for intent={intent}, "
                    f"region={region}, user={update.effective_user.id}"
                )
            else:
                # No links found
                response = self.formatter_service.format_error_response("no_links", user_language)
                await update.message.reply_text(response)

                self.logger.warning(f"No links found for intent={intent}, region={region}")

        except Exception as e:
            self.logger.error(f"Error sending links response: {e}")
            error_response = self.formatter_service.format_error_response("generic", user_language)
            await update.message.reply_text(error_response)

    async def handle_region_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """
        Handle region selection in conversation.

        This handler is called when the bot is waiting for the user to
        specify a region for their request.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            int: Conversation state (END or ASK_REGION)
        """
        user_language = update.effective_user.language_code if update.effective_user else None
        region_text = (update.message.text or "").strip()

        # Get pending intent from context
        pending_intent = context.user_data.get("pending_intent")
        pending_request = context.user_data.get("pending_request")

        if not pending_intent:
            # No pending intent, something went wrong
            self.logger.warning("Region handler called but no pending intent found")
            response = self.formatter_service.format_error_response("generic", user_language)
            await update.message.reply_text(response)
            return ConversationHandler.END

        if not region_text:
            # Empty region input, ask again with examples
            regions = self.catalog_service.get_regions()
            example_regions = regions[:5] if regions else []

            response = self.formatter_service.format_region_request(example_regions, user_language)
            await update.message.reply_text(response)
            return ConversationState.ASK_REGION.value

        # Validate region input
        validation_result = self.validation_service.validate_region(region_text)

        if validation_result.is_valid:
            # Valid region provided
            normalized_region = validation_result.normalized_value

            # Send links response
            await self._send_links_response(pending_intent, normalized_region, update)

            # Clean up context
            context.user_data.pop("pending_intent", None)
            context.user_data.pop("pending_request", None)

            self.logger.info(
                f"Region conversation completed: intent={pending_intent}, "
                f"region={normalized_region}, user={update.effective_user.id}"
            )

            return ConversationHandler.END

        else:
            # Invalid region, provide suggestions
            response = self.formatter_service.format_region_suggestions(
                region_text, validation_result.suggestions or [], user_language
            )

            await update.message.reply_text(response)

            self.logger.info(
                f"Invalid region '{region_text}' provided by user {update.effective_user.id}. "
                f"Suggestions: {validation_result.suggestions}"
            )

            # Stay in region selection state
            return ConversationState.ASK_REGION.value

    def create_conversation_handler(
        self, entry_points: list, fallbacks: list
    ) -> ConversationHandler:
        """
        Create a ConversationHandler with the region selection flow.

        Args:
            entry_points: List of handlers that can start the conversation
            fallbacks: List of fallback handlers

        Returns:
            ConversationHandler: Configured conversation handler
        """
        return ConversationHandler(
            entry_points=entry_points,
            states={ConversationState.ASK_REGION.value: [self.region_handler]},
            fallbacks=fallbacks,
            name="region_conversation",
            persistent=False,
            allow_reentry=True,  # Allow users to restart conversation
            conversation_timeout=300,  # 5 minutes timeout
        )

    async def _handle_conversation_timeout(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle conversation timeout.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        # Clean up context
        context.user_data.pop("pending_intent", None)
        context.user_data.pop("pending_request", None)

        # Notify user
        response = self.formatter_service.format_error_response(
            "generic", user_language  # You might want to add a specific timeout message
        )

        try:
            await update.message.reply_text(response)
        except Exception as e:
            self.logger.error(f"Failed to send timeout message: {e}")

        self.logger.info(f"Conversation timed out for user {update.effective_user.id}")

    def get_active_conversations_count(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Get count of active conversations.

        Args:
            context: Telegram context object

        Returns:
            int: Number of active conversations
        """
        # This is a simplified implementation
        # In a real application, you might want to track this more precisely
        try:
            return len([key for key in context.user_data.keys() if key.startswith("pending_")])
        except Exception:
            return 0

    def clear_conversation_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Clear conversation state from context.

        Args:
            context: Telegram context object
        """
        try:
            context.user_data.pop("pending_intent", None)
            context.user_data.pop("pending_request", None)
            self.logger.debug("Conversation state cleared")
        except Exception as e:
            self.logger.error(f"Error clearing conversation state: {e}")

    def get_conversation_state(self, context: ContextTypes.DEFAULT_TYPE) -> dict:
        """
        Get current conversation state information.

        Args:
            context: Telegram context object

        Returns:
            dict: Conversation state information
        """
        return {
            "pending_intent": context.user_data.get("pending_intent"),
            "pending_request": context.user_,
        }
