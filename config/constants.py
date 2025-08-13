"""
Application Constants Module

This module contains all application-wide constants, including intent types,
conversation states, regex patterns, and default messages.

Constants:
    IntentType: Enumeration of all supported intent types
    ConversationState: Enumeration of conversation states
    HELP_PATTERNS: Regex patterns for help-related messages
    ABOUT_PATTERNS: Regex patterns for about-related messages
    DEFAULT_GREETING_MESSAGES: Default greeting responses
    DEFAULT_SMALLTALK_MESSAGES: Default smalltalk responses
    NATIONAL_REGION: Constant for national-level services
"""

import re
from enum import Enum
from typing import List, Pattern


class IntentType(Enum):
    """
    Enumeration of all supported intent types.

    These represent the different types of requests the bot can handle.
    Each intent corresponds to a specific type of public service or interaction.
    """

    # Conversational intents
    GREETING = "greeting"
    SMALLTALK = "smalltalk"
    HELP = "help"
    ABOUT = "about"
    OFF_TOPIC = "off_topic"

    # Service intents (region-dependent)
    FASCICOLO_SANITARIO = "fascicolo_sanitario"  # Health records
    BOLLO_AUTO = "bollo_auto"  # Car tax
    CUP = "cup"  # Medical booking system

    # Service intents (national)
    PATENTE = "patente"  # Driving license
    ANPR = "anpr"  # Registry certificates
    IO_APP = "io_app"  # IO App
    PAGOPA = "pagopa"  # PagoPA payment system
    SCUOLA = "scuola"  # School services
    TARI = "tari"  # Waste tax

    # New intents from updated JSON
    SPID = "spid"  # Digital identity SPID
    CIE = "cie"  # Electronic ID card
    INPS = "inps"  # Social security
    AGENZIA_ENTRATE = "agenzia_entrate"  # Tax authority

    UNKNOWN = "unknown"  # Fallback for unrecognized intents

    @classmethod
    def requires_region(cls, intent: str) -> bool:
        """
        Check if an intent requires region specification.

        Args:
            intent: Intent string to check

        Returns:
            bool: True if intent requires region, False otherwise
        """
        region_dependent_intents = {
            cls.FASCICOLO_SANITARIO.value,
            cls.BOLLO_AUTO.value,
            cls.CUP.value,
        }
        return intent in region_dependent_intents

    @classmethod
    def is_conversational(cls, intent: str) -> bool:
        """
        Check if an intent is conversational (doesn't provide links).

        Args:
            intent: Intent string to check

        Returns:
            bool: True if intent is conversational, False otherwise
        """
        conversational_intents = {
            cls.GREETING.value,
            cls.SMALLTALK.value,
            cls.HELP.value,
            cls.ABOUT.value,
            cls.OFF_TOPIC.value,
        }
        return intent in conversational_intents

    @classmethod
    def get_all_service_intents(cls) -> List[str]:
        """
        Get all service-related intents (those that provide links).

        Returns:
            List[str]: List of all service intent values
        """
        return [
            cls.FASCICOLO_SANITARIO.value,
            cls.BOLLO_AUTO.value,
            cls.CUP.value,
            cls.PATENTE.value,
            cls.ANPR.value,
            cls.IO_APP.value,
            cls.PAGOPA.value,
            cls.SCUOLA.value,
            cls.TARI.value,
            cls.SPID.value,
            cls.CIE.value,
            cls.INPS.value,
            cls.AGENZIA_ENTRATE.value,
        ]


class ConversationState(Enum):
    """
    Enumeration of conversation states for ConversationHandler.

    These represent different states in multi-step conversations,
    particularly when gathering additional information from users.
    """

    ASK_REGION = 0  # Waiting for user to specify a region


# Regex patterns for intent detection
HELP_PATTERNS: List[Pattern[str]] = [
    re.compile(r"\bhelp\b", re.IGNORECASE),
    re.compile(r"\baiuto\b", re.IGNORECASE),
    re.compile(r"\bcosa\s+sai\s+fare\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+can\s+you\s+do\b", re.IGNORECASE),
    re.compile(r"\bcomandi\b", re.IGNORECASE),
    re.compile(r"\bfunzioni\b", re.IGNORECASE),
]

ABOUT_PATTERNS: List[Pattern[str]] = [
    re.compile(r"\bchi\s+sei\b", re.IGNORECASE),
    re.compile(r"\bwho\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bcosa\s+sei\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+are\s+you\b", re.IGNORECASE),
]

# Default response messages
DEFAULT_GREETING_MESSAGES: List[str] = [
    "Hi there! 👋 Ready to serve your links al dente 🍝",
    "Hey! I'm here to untangle your public service spaghetti 😉",
    "Hello! Tell me what you need and I'll link it in one click.",
    "Ciao! What public service can I help you with today? 🇮🇹",
]

DEFAULT_SMALLTALK_MESSAGES: List[str] = [
    "All good here! Stirring some links in the pot 😄",
    "Thanks! Ask me about car tax, health records, driving license, CUP…",
    "Always online: pixels, pasta, and public administration!",
    "Everything's running smoothly! How can I help with Italian services?",
]

# Special region constant
NATIONAL_REGION = "Nazionale"

# Message limits
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
SAFE_MESSAGE_LENGTH = 4000  # Leave some buffer

# Cache configuration
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour
DEFAULT_CLASSIFICATION_CACHE_SIZE = 1000
DEFAULT_LINKS_CACHE_SIZE = 500

# Input validation
MIN_MESSAGE_LENGTH = 3
MAX_SPAM_REPETITION_RATIO = 0.3  # Max ratio of unique chars to total chars for spam detection
MIN_UNIQUE_CHARS_FOR_SPAM_CHECK = 3

# Bot metadata
BOT_NAME = "PAstaLinkBot"
BOT_AUTHOR = "PastaBits"
BOT_VERSION = "1.0.0"
BOT_DESCRIPTION = "I give you the official links to Italian public services without wasting time."

# Error messages
ERROR_MESSAGES = {
    "generic": "Sorry, something went wrong. Please try again.",
    "no_links": "I couldn't find any links for your request.",
    "invalid_region": "I didn't recognize that region. Please try again.",
    "message_too_long": "Message too long. Please keep it under {max_length} characters.",
    "spam_detected": "Please send a meaningful message.",
    "admin_only": "Sorry, this command is only available for administrators.",
    "no_message": "Please send me a message.",
}

# Success messages
SUCCESS_MESSAGES = {
    "links_header": "Useful links ({intent})",
    "region_examples": "For which region? (e.g. {examples})",
    "suggestions": "I didn't recognize '{region}'. Did you mean: {suggestions}?",
    "popular_regions": "I didn't recognize '{region}'. Try one of these: {popular}",
}

# Help text templates
HELP_TEXT_TEMPLATE = """Here's what I can do:

**Health Services:**
• Health records / prescriptions / reports (per region)
• CUP medical appointments booking (per region)

**Vehicle Services:**
• Car tax calculation and payment
• Driving license renewal

**Digital Identity:**
• SPID (Digital Identity System)
• CIE (Electronic ID Card)

**Government Services:**
• ANPR registry certificates
• IO App / PagoPA services
• School enrollment services
• INPS social security services
• Agenzia delle Entrate (tax services)
• Waste tax (TARI) information

**Examples:**
• *"Where do I see the doctor's prescriptions in Lombardia?"*
• *"Book a medical visit in Tuscany"*
• *"How do I calculate car tax?"*
• *"How to get SPID?"*
• *"Download IO app"*"""

ABOUT_TEXT_TEMPLATE = f"""I'm **{BOT_NAME}** by {BOT_AUTHOR} 🍝
{BOT_DESCRIPTION}
No personal data: just quick links and clear instructions."""

STATS_TEXT_TEMPLATE = """📊 **Bot Statistics**

**Catalog Index:**
• Total entries: {total_entries}
• Intents indexed: {intents}
• Regions available: {regions}

**Links Cache:**
• Hits: {links_hits}
• Misses: {links_misses}
• Current size: {links_current}
• Max size: {links_max}

**LLM Classification Cache:**
• Hits: {classify_hits}
• Misses: {classify_misses}
• Current size: {classify_current}
• Max size: {classify_max}

**Input Validator:**
• Total regions: {validator_regions}
• Region aliases: {validator_aliases}"""

REGIONS_TEXT_TEMPLATE = """**Available regions** ({total} total):
{regions}

_Use /regions to see all_"""
