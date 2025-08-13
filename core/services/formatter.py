"""
Response Formatter Service

This module handles formatting of bot responses including links, messages,
and internationalization support.

Classes:
    ResponseFormatterService: Main service for response formatting
"""

import logging
import random
from typing import Any, Dict, List, Optional

from telegram.constants import ParseMode

from config.constants import (
    ABOUT_TEXT_TEMPLATE,
    BOT_NAME,
    DEFAULT_GREETING_MESSAGES,
    DEFAULT_SMALLTALK_MESSAGES,
    ERROR_MESSAGES,
    HELP_TEXT_TEMPLATE,
    REGIONS_TEXT_TEMPLATE,
    SAFE_MESSAGE_LENGTH,
    STATS_TEXT_TEMPLATE,
    SUCCESS_MESSAGES,
)
from core.models.intent import CatalogEntry
from utils.i18n import get_translator
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class ResponseFormatterService(LoggerMixin):
    """
    Service for formatting bot responses with i18n support.

    This service handles all response formatting including link lists,
    help messages, error messages, and internationalization.
    """

    def __init__(
        self,
        max_links: int = 6,
        regions_per_message: int = 15,
        default_language: str = "it",
    ):
        """
        Initialize response formatter service.

        Args:
            max_links: Maximum number of links to include in responses
            regions_per_message: Number of regions to show per message
            default_language: Default language code for translations
        """
        self.max_links = max_links
        self.regions_per_message = regions_per_message
        self.default_language = default_language

        self.logger.info("Response formatter service initialized")

    def format_links_response(
        self,
        entries: List[CatalogEntry],
        intent: str,
        user_language: Optional[str] = None,
    ) -> str:
        """
        Format a list of catalog entries into a user-friendly message.

        Args:
            entries: List of catalog entries to format
            intent: Intent name for the header
            user_language: User's language code for i18n

        Returns:
            str: Formatted response message
        """
        _ = get_translator(user_language or self.default_language)

        if not entries:
            return _(ERROR_MESSAGES["no_links"])

        # Limit entries
        limited_entries = entries[: self.max_links]

        # Create header
        intent_display = intent.replace("_", " ").title()
        header = _(SUCCESS_MESSAGES["links_header"]).format(intent=intent_display)

        # Format links
        link_items = []
        for entry in limited_entries:
            if entry.url:  # Only add if URL exists
                link_items.append(f"• {entry.label}: {entry.url}")

        if not link_items:
            return _(ERROR_MESSAGES["no_links"])

        # Combine header and links
        message = f"{header}\n\n" + "\n".join(link_items)

        # Check message length and truncate if needed
        if len(message) > SAFE_MESSAGE_LENGTH:
            message = message[:SAFE_MESSAGE_LENGTH] + "\n..."
            self.logger.warning("Response message truncated due to length")

        return message

    def format_greeting_response(self, user_language: Optional[str] = None) -> str:
        """
        Format a random greeting response.

        Args:
            user_language: User's language code for i18n

        Returns:
            str: Formatted greeting message
        """
        _ = get_translator(user_language or self.default_language)

        # Get translated greeting messages or fall back to defaults
        try:
            greeting_messages = [
                _("Hi there! 👋 Ready to serve your links al dente 🍝"),
                _("Hey! I'm here to untangle your public service spaghetti 😉"),
                _("Hello! Tell me what you need and I'll link it in one click."),
                _("Ciao! What public service can I help you with today? 🇮🇹"),
            ]
        except:
            greeting_messages = DEFAULT_GREETING_MESSAGES

        return random.choice(greeting_messages)

    def format_smalltalk_response(self, user_language: Optional[str] = None) -> str:
        """
        Format a random smalltalk response.

        Args:
            user_language: User's language code for i18n

        Returns:
            str: Formatted smalltalk message
        """
        _ = get_translator(user_language or self.default_language)

        try:
            smalltalk_messages = [
                _("All good here! Stirring some links in the pot 😄"),
                _("Thanks! Ask me about car tax, health records, driving license, CUP…"),
                _("Always online: pixels, pasta, and public administration!"),
                _("Everything's running smoothly! How can I help with Italian services?"),
            ]
        except:
            smalltalk_messages = DEFAULT_SMALLTALK_MESSAGES

        return random.choice(smalltalk_messages)

    def format_help_response(self, user_language: Optional[str] = None) -> str:
        """
        Format help response message.

        Args:
            user_language: User's language code for i18n

        Returns:
            str: Formatted help message
        """
        _ = get_translator(user_language or self.default_language)

        try:
            return _(HELP_TEXT_TEMPLATE)
        except:
            return HELP_TEXT_TEMPLATE

    def format_about_response(self, user_language: Optional[str] = None) -> str:
        """
        Format about response message.

        Args:
            user_language: User's language code for i18n

        Returns:
            str: Formatted about message
        """
        _ = get_translator(user_language or self.default_language)

        try:
            return _(ABOUT_TEXT_TEMPLATE)
        except:
            return ABOUT_TEXT_TEMPLATE

    def format_off_topic_response(self, user_language: Optional[str] = None) -> str:
        """
        Format off-topic response message.

        Args:
            user_language: User's language code for i18n

        Returns:
            str: Formatted off-topic message
        """
        _ = get_translator(user_language or self.default_language)

        message = _(
            "I deal with **Italian public services**: health record/recipes, car tax, driving license, "
            "ANPR/certificates, IO/PagoPA, CUP, school, waste tax.\n"
            'Try: *"Where do I pay the car tax in Lombardia"* or *"Where do I see the doctor\'s prescriptions?"*'
        )

        return message

    def format_region_request(
        self, example_regions: List[str], user_language: Optional[str] = None
    ) -> str:
        """
        Format a region request message with examples.

        Args:
            example_regions: List of example regions to show
            user_language: User's language code for i18n

        Returns:
            str: Formatted region request message
        """
        _ = get_translator(user_language or self.default_language)

        if example_regions:
            examples_text = ", ".join(example_regions[:3])  # Show max 3 examples
            message = _(SUCCESS_MESSAGES["region_examples"]).format(examples=examples_text)
        else:
            message = _("For which region?")

        return message

    def format_region_suggestions(
        self,
        invalid_region: str,
        suggestions: List[str],
        user_language: Optional[str] = None,
    ) -> str:
        """
        Format region suggestions for invalid input.

        Args:
            invalid_region: The invalid region input
            suggestions: List of suggested regions
            user_language: User's language code for i18n

        Returns:
            str: Formatted suggestions message
        """
        _ = get_translator(user_language or self.default_language)

        if suggestions:
            suggestions_text = ", ".join(suggestions)
            message = _(SUCCESS_MESSAGES["suggestions"]).format(
                region=invalid_region, suggestions=suggestions_text
            )
        else:
            # No suggestions available
            message = _("I didn't recognize '{region}'. Please try again.").format(
                region=invalid_region
            )

        return message

    def format_regions_list(self, regions: List[str], user_language: Optional[str] = None) -> str:
        """
        Format list of available regions.

        Args:
            regions: List of regions to display
            user_language: User's language code for i18n

        Returns:
            str: Formatted regions list message
        """
        _ = get_translator(user_language or self.default_language)

        if not regions:
            return _("No regions are currently available.")

        total_regions = len(regions)

        if total_regions <= self.regions_per_message:
            # Show all regions in one message
            regions_text = ", ".join(sorted(regions))
            message = _("**Available regions:**\n{regions}").format(regions=regions_text)
        else:
            # Show first batch with count
            first_batch = sorted(regions)[: self.regions_per_message]
            regions_text = ", ".join(first_batch)

            message = _(REGIONS_TEXT_TEMPLATE).format(total=total_regions, regions=regions_text)

        return message

    def format_stats_response(
        self, stats_data: Dict[str, Any], user_language: Optional[str] = None
    ) -> str:
        """
        Format statistics response message.

        Args:
            stats_data: Dictionary containing statistics data
            user_language: User's language code for i18n

        Returns:
            str: Formatted statistics message
        """
        _ = get_translator(user_language or self.default_language)

        try:
            # Extract data with safe defaults
            index_stats = stats_data.get("index", {})
            cache_stats = stats_data.get("cache", {})
            validator_stats = stats_data.get("validator", {})

            message = _(STATS_TEXT_TEMPLATE).format(
                total_entries=index_stats.get("total_entries", 0),
                intents=index_stats.get("intents", 0),
                regions=index_stats.get("regions", 0),
                links_hits=index_stats.get("cache_hits", 0),
                links_misses=index_stats.get("cache_misses", 0),
                links_current=index_stats.get("cache_size", 0),
                links_max=index_stats.get("cache_maxsize", 0),
                classify_hits=cache_stats.get("hits", 0),
                classify_misses=cache_stats.get("misses", 0),
                classify_current=cache_stats.get("currsize", 0),
                classify_max=cache_stats.get("maxsize", 0),
                validator_regions=validator_stats.get("total_regions", 0),
                validator_aliases=validator_stats.get("aliases", 0),
            )

            return message

        except Exception as e:
            self.logger.error(f"Error formatting stats response: {e}")
            return _("Error retrieving statistics.")

    def format_error_response(
        self, error_key: str, user_language: Optional[str] = None, **format_args
    ) -> str:
        """
        Format error response message.

        Args:
            error_key: Key from ERROR_MESSAGES constant
            user_language: User's language code for i18n
            **format_args: Arguments for string formatting

        Returns:
            str: Formatted error message
        """
        _ = get_translator(user_language or self.default_language)

        try:
            error_template = ERROR_MESSAGES.get(error_key, ERROR_MESSAGES["generic"])
            message = _(error_template).format(**format_args)
            return message
        except Exception as e:
            self.logger.error(f"Error formatting error response: {e}")
            return _(ERROR_MESSAGES["generic"])

    def format_validation_error(
        self,
        error_message: str,
        suggestions: Optional[List[str]] = None,
        user_language: Optional[str] = None,
    ) -> str:
        """
        Format validation error with optional suggestions.

        Args:
            error_message: The validation error message
            suggestions: Optional suggestions to include
            user_language: User's language code for i18n

        Returns:
            str: Formatted validation error message
        """
        _ = get_translator(user_language or self.default_language)

        message = _(error_message)

        if suggestions:
            suggestions_text = ", ".join(suggestions)
            message += f"\n\n{_('Suggestions')}: {suggestions_text}"

        return message

    def truncate_message(self, message: str, max_length: int = SAFE_MESSAGE_LENGTH) -> str:
        """
        Truncate message to safe length if needed.

        Args:
            message: Message to truncate
            max_length: Maximum allowed length

        Returns:
            str: Truncated message if needed
        """
        if len(message) <= max_length:
            return message

        truncated = message[: max_length - 4] + "..."
        self.logger.warning(f"Message truncated from {len(message)} to {len(truncated)} characters")
        return truncated

    def get_parse_mode(self, content: str) -> Optional[str]:
        """
        Determine appropriate parse mode for message content.

        Args:
            content: Message content to analyze

        Returns:
            Optional[str]: Parse mode (Markdown, HTML, or None)
        """
        # Check for Markdown indicators
        if any(indicator in content for indicator in ["**", "*", "_", "`", "["]):
            return ParseMode.MARKDOWN

        # Check for HTML indicators
        if any(indicator in content for indicator in ["<b>", "<i>", "<u>", "<code>"]):
            return ParseMode.HTML

        return None
