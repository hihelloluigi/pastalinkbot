"""
Configuration package for PAstaLinkBot.

This package contains all configuration-related modules including
settings management and application constants.
"""

from .constants import ConversationState, IntentType
from .settings import Settings, load_settings

__all__ = ["Settings", "load_settings", "IntentType", "ConversationState"]
