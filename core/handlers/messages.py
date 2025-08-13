"""
Message Handlers

This module contains handlers for processing user messages, including
intent classification, validation, and response generation.

Classes:
    MessageHandlers: Main class for message processing
"""

import logging
import re
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes, MessageHandler, filters

from config.constants import (
    ABOUT_PATTERNS,
    HELP_PATTERNS,
    ConversationState,
    IntentType,
)
from core.models.intent import IntentRequest
from core.services.catalog import CatalogService
from core.services.classifier import ClassificationService
from core.services.formatter import ResponseFormatterService
from core.services.validator import InputValidationService
from utils.decorators import handle_telegram_errors, log_handler_call, validate_update
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class MessageHandlers(LoggerMixin):
    """
    Handler class for processing user messages.

    This class handles all text messages from users, including classification,
    validation, and response generation.
    """

    def __init__(
        self,
        catalog_service: CatalogService,
        validation_service: InputValidationService,
        classification_service: ClassificationService,
        formatter_service: ResponseFormatterService,
    ):
        """
        Initialize message handlers.

        Args:
            catalog_service: Service for catalog operations
            validation_service: Service for input validation
            classification_service: Service for intent classification
            formatter_service: Service for response formatting
        """
        self.catalog_service = catalog_service
        self.validation_service = validation_service
        self.classification_service = classification_service
        self.formatter_service = formatter_service

        # Create handler instance with decorated standalone wrapper
        self.message_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._create_handler_wrapper()
        )

    def _create_handler_wrapper(self):
        """
        Create a standalone wrapper function with decorators.

        This creates a function that can be called by Telegram without 'self'.
        """

        @handle_telegram_errors
        @log_handler_call
        @validate_update
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
            """
            Standalone wrapper function for handle_message with decorators.
            """
            return await self.handle_message(update, context)

        return wrapper

        self.logger.info("Message handlers initialized")

    def _matches_patterns(self, text: str, patterns: list) -> bool:
        """
        Check if text matches any of the given regex patterns.

        Args:
            text: Text to check
            patterns: List of regex patterns

        Returns:
            bool: True if text matches any pattern
        """
        try:
            text_lower = text.lower() if text else ""
            return any(pattern.search(text_lower) for pattern in patterns)
        except Exception as e:
            self.logger.error(f"Error in pattern matching: {e}")
            return False

    async def _send_typing_indicator(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[any]:
        """
        Send typing indicator and placeholder message.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Optional[any]: Placeholder message object or None
        """
        try:
            # Send typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING
            )

            # Send placeholder message
            placeholder = await update.message.reply_text("🧠...")
            return placeholder

        except Exception as e:
            self.logger.error(f"Failed to send typing indicator: {e}")
            return None

    async def _handle_conversational_intent(
        self,
        intent: str,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder: Optional[any] = None,
    ) -> None:
        """
        Handle conversational intents (greeting, help, etc.).

        Args:
            intent: The classified intent
            update: Telegram update object
            context: Telegram context object
            placeholder: Optional placeholder message to edit
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        if intent == IntentType.GREETING.value:
            response = self.formatter_service.format_greeting_response(user_language)
        elif intent == IntentType.SMALLTALK.value:
            response = self.formatter_service.format_smalltalk_response(user_language)
        elif intent == IntentType.HELP.value:
            response = self.formatter_service.format_help_response(user_language)
        elif intent == IntentType.ABOUT.value:
            response = self.formatter_service.format_about_response(user_language)
        elif intent == IntentType.OFF_TOPIC.value:
            response = self.formatter_service.format_off_topic_response(user_language)
        else:
            response = self.formatter_service.format_error_response("generic", user_language)

        # Send response
        parse_mode = self.formatter_service.get_parse_mode(response)

        if placeholder:
            try:
                await placeholder.edit_text(response, parse_mode=parse_mode)
            except Exception as e:
                self.logger.error(f"Failed to edit placeholder: {e}")
                await update.message.reply_text(response, parse_mode=parse_mode)
        else:
            await update.message.reply_text(response, parse_mode=parse_mode)

    async def _handle_service_intent(
        self,
        intent_request: IntentRequest,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder: Optional[any] = None,
    ) -> Optional[int]:
        """
        Handle service intents that provide links.

        Args:
            intent_request: The classified intent request
            update: Telegram update object
            context: Telegram context object
            placeholder: Optional placeholder message to edit

        Returns:
            Optional[int]: Conversation state if region is needed, None otherwise
        """
        user_language = update.effective_user.language_code if update.effective_user else None
        classification = intent_request.classification

        # Check if intent requires region but none provided
        if (
            classification.requires_region
            and not classification.region
            and classification.needs_region
        ):
            # Store intent for later and ask for region
            context.user_data["pending_intent"] = classification.intent
            context.user_data["pending_request"] = intent_request

            # Get example regions for display
            regions = self.catalog_service.get_regions()
            example_regions = regions[:3] if regions else []

            response = self.formatter_service.format_region_request(example_regions, user_language)

            if placeholder:
                try:
                    await placeholder.edit_text(response)
                except Exception as e:
                    self.logger.error(f"Failed to edit placeholder: {e}")
                    await update.message.reply_text(response)
            else:
                await update.message.reply_text(response)

            return ConversationState.ASK_REGION.value

        # We have enough info to provide links
        if placeholder:
            try:
                await placeholder.delete()
            except Exception as e:
                self.logger.error(f"Failed to delete placeholder: {e}")

        await self._send_links_response(intent_request, update)
        return None

    async def _send_links_response(self, intent_request: IntentRequest, update: Update) -> None:
        """
        Send links response to user.

        Args:
            intent_request: The intent request with classification
            update: Telegram update object
        """
        user_language = update.effective_user.language_code if update.effective_user else None

        try:
            # Get links from catalog
            links = self.catalog_service.get_links(intent_request.intent, intent_request.region)

            if links:
                # Format and send links
                response = self.formatter_service.format_links_response(
                    links, intent_request.intent, user_language
                )
                await update.message.reply_text(response)

                self.logger.info(
                    f"Sent {len(links)} links for intent={intent_request.intent}, "
                    f"region={intent_request.region}, user={update.effective_user.id}"
                )
            else:
                # No links found
                response = self.formatter_service.format_error_response("no_links", user_language)
                await update.message.reply_text(response)

                self.logger.warning(
                    f"No links found for intent={intent_request.intent}, "
                    f"region={intent_request.region}"
                )

        except Exception as e:
            self.logger.error(f"Error sending links response: {e}")
            error_response = self.formatter_service.format_error_response("generic", user_language)
            await update.message.reply_text(error_response)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[int]:
        """
        Main message handler.

        Processes user messages through validation, classification, and response generation.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Optional[int]: Conversation state if transitioning to conversation
        """
        user_language = update.effective_user.language_code if update.effective_user else None
        raw_text = update.message.text or ""

        # Validate message
        validation_result = self.validation_service.validate_message(raw_text)
        if not validation_result.is_valid:
            error_response = self.formatter_service.format_validation_error(
                validation_result.error_message,
                validation_result.suggestions,
                user_language,
            )
            await update.message.reply_text(error_response)
            return None

        text = validation_result.normalized_value

        # Check for pattern-based overrides (help/about)
        if self._matches_patterns(text, HELP_PATTERNS):
            response = self.formatter_service.format_help_response(user_language)
            parse_mode = self.formatter_service.get_parse_mode(response)
            await update.message.reply_text(response, parse_mode=parse_mode)
            return None

        if self._matches_patterns(text, ABOUT_PATTERNS):
            response = self.formatter_service.format_about_response(user_language)
            parse_mode = self.formatter_service.get_parse_mode(response)
            await update.message.reply_text(response, parse_mode=parse_mode)
            return None

        # Send typing indicator
        placeholder = await self._send_typing_indicator(update, context)

        try:
            # Classify intent
            classification = await self.classification_service.classify_async(text)

            # Normalize region if provided by LLM
            if classification.region:
                region_validation = self.validation_service.validate_region(classification.region)
                if region_validation.is_valid:
                    classification.region = region_validation.normalized_value
                else:
                    self.logger.warning(f"LLM provided invalid region: {classification.region}")
                    classification.region = None

            # Create intent request
            intent_request = IntentRequest(
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                message_text=text,
                classification=classification,
                user_language=user_language,
            )

            # Handle based on intent type
            if classification.is_conversational:
                await self._handle_conversational_intent(
                    classification.intent, update, context, placeholder
                )
                return None
            else:
                # Service intent - may return conversation state
                return await self._handle_service_intent(
                    intent_request, update, context, placeholder
                )

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

            # Send error response
            error_response = self.formatter_service.format_error_response("generic", user_language)

            if placeholder:
                try:
                    await placeholder.edit_text(error_response)
                except Exception:
                    await update.message.reply_text(error_response)
            else:
                await update.message.reply_text(error_response)

            return None
