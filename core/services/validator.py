"""
Input Validation Service

This module provides comprehensive input validation and normalization services,
including region validation, text sanitization, and spam detection.

Classes:
    ValidationResult: Result of input validation
    InputValidationService: Main validation service
"""

import difflib
import logging
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from config.constants import (
    MAX_SPAM_REPETITION_RATIO,
    MIN_MESSAGE_LENGTH,
    MIN_UNIQUE_CHARS_FOR_SPAM_CHECK,
)
from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of input validation.

    Attributes:
        is_valid: Whether the input is valid
        normalized_value: Normalized/sanitized input value
        error_message: Error message if validation failed
        suggestions: List of suggestions for invalid input
        original_value: Original input value for reference
    """

    is_valid: bool
    normalized_value: Optional[str] = None
    error_message: Optional[str] = None
    suggestions: Optional[List[str]] = None
    original_value: Optional[str] = None

    @classmethod
    def valid(cls, normalized_value: str, original_value: str = None) -> "ValidationResult":
        """Create a valid validation result."""
        return cls(
            is_valid=True,
            normalized_value=normalized_value,
            original_value=original_value or normalized_value,
        )

    @classmethod
    def invalid(
        cls,
        error_message: str,
        original_value: str = None,
        suggestions: List[str] = None,
    ) -> "ValidationResult":
        """Create an invalid validation result."""
        return cls(
            is_valid=False,
            error_message=error_message,
            original_value=original_value,
            suggestions=suggestions or [],
        )


class InputValidationService(LoggerMixin):
    """
    Comprehensive input validation and normalization service.

    This service handles validation of user input including region names,
    message content, and general text sanitization.
    """

    def __init__(
        self,
        regions: List[str],
        max_message_length: int = 1000,
        fuzzy_match_threshold: float = 0.7,
        suggestion_threshold: float = 0.4,
    ):
        """
        Initialize validation service.

        Args:
            regions: List of valid region names
            max_message_length: Maximum allowed message length
            fuzzy_match_threshold: Minimum similarity for fuzzy matching
            suggestion_threshold: Minimum similarity for suggestions
        """
        self.regions = set(regions)
        self.max_message_length = max_message_length
        self.fuzzy_match_threshold = fuzzy_match_threshold
        self.suggestion_threshold = suggestion_threshold

        # Build normalized region mappings
        self.normalized_regions = {self._normalize_text(r): r for r in regions}

        # Build region aliases
        self.region_aliases = self._build_region_aliases()

        self.logger.info(
            f"Input validator initialized with {len(self.regions)} regions, "
            f"{len(self.region_aliases)} aliases"
        )

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            str: Normalized text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower().strip()

        # Remove accents and diacritics
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        # Normalize punctuation
        text = text.replace("'", "'").replace("'", "'")  # Normalize apostrophes
        text = text.replace("-", " ").replace("_", " ")  # Normalize separators

        # Remove extra whitespace
        text = " ".join(text.split())

        return text

    def _build_region_aliases(self) -> Dict[str, str]:
        """
        Build region aliases mapping.

        Returns:
            Dict[str, str]: Mapping from alias to canonical region name
        """
        aliases = {}

        # Common Italian region aliases
        region_mappings = {
            # English names
            "lombardy": "Lombardia",
            "piedmont": "Piemonte",
            "tuscany": "Toscana",
            "sicily": "Sicilia",
            "sardinia": "Sardegna",
            "apulia": "Puglia",
            # City to region mappings
            "roma": "Lazio",
            "rome": "Lazio",
            "milano": "Lombardia",
            "milan": "Lombardia",
            "napoli": "Campania",
            "naples": "Campania",
            "torino": "Piemonte",
            "turin": "Piemonte",
            "firenze": "Toscana",
            "florence": "Toscana",
            "bologna": "Emilia-Romagna",
            "venezia": "Veneto",
            "venice": "Veneto",
            "genova": "Liguria",
            "genoa": "Liguria",
            "bari": "Puglia",
            "palermo": "Sicilia",
            "catania": "Sicilia",
            # Alternative spellings
            "emilia romagna": "Emilia-Romagna",
            "friuli venezia giulia": "Friuli-Venezia Giulia",
            "trentino alto adige": "Trentino-Alto Adige",
            "valle daosta": "Valle d'Aosta",
        }

        # Add normalized versions of mappings
        for alias, region in region_mappings.items():
            normalized_alias = self._normalize_text(alias)
            if region in self.regions:
                aliases[normalized_alias] = region

        # Add normalized versions of actual region names
        for region in self.regions:
            normalized = self._normalize_text(region)
            aliases[normalized] = region

        return aliases

    def validate_message_length(self, text: str) -> ValidationResult:
        """
        Validate message length.

        Args:
            text: Message text to validate

        Returns:
            ValidationResult: Validation result
        """
        if not text:
            return ValidationResult.invalid("Message cannot be empty", original_value=text)

        if len(text) < MIN_MESSAGE_LENGTH:
            return ValidationResult.invalid(
                f"Message too short (minimum {MIN_MESSAGE_LENGTH} characters)",
                original_value=text,
            )

        if len(text) > self.max_message_length:
            return ValidationResult.invalid(
                f"Message too long (maximum {self.max_message_length} characters)",
                original_value=text,
            )

        return ValidationResult.valid(text)

    def detect_spam(self, text: str) -> ValidationResult:
        """
        Detect spam-like content.

        Args:
            text: Text to check for spam

        Returns:
            ValidationResult: Validation result
        """
        if not text:
            return ValidationResult.valid(text)

        # Check for excessive repetition
        if len(text) > MIN_UNIQUE_CHARS_FOR_SPAM_CHECK:
            unique_chars = len(set(text.lower()))
            total_chars = len(text)
            repetition_ratio = unique_chars / total_chars

            if repetition_ratio < MAX_SPAM_REPETITION_RATIO:
                return ValidationResult.invalid(
                    "Message appears to be spam (too repetitive)", original_value=text
                )

        # Check for excessive punctuation
        punctuation_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if len(text) > 10 and punctuation_count / len(text) > 0.5:
            return ValidationResult.invalid(
                "Message contains excessive punctuation", original_value=text
            )

        return ValidationResult.valid(text)

    def sanitize_input(self, text: str) -> str:
        """
        Sanitize user input by removing problematic characters.

        Args:
            text: Text to sanitize

        Returns:
            str: Sanitized text
        """
        if not text:
            return ""

        # Remove control characters except newlines and tabs
        sanitized = "".join(c for c in text if c.isprintable() or c in "\n\t")

        # Limit consecutive whitespace
        sanitized = " ".join(sanitized.split())

        return sanitized.strip()

    def validate_region(self, region_text: str) -> ValidationResult:
        """
        Validate and normalize region input.

        Args:
            region_text: Region text to validate

        Returns:
            ValidationResult: Validation result with normalized region or suggestions
        """
        if not region_text:
            return ValidationResult.invalid("Region cannot be empty", original_value=region_text)

        original_text = region_text.strip()
        sanitized_text = self.sanitize_input(original_text)
        normalized_input = self._normalize_text(sanitized_text)

        # Direct match with normalization
        if normalized_input in self.normalized_regions:
            canonical_region = self.normalized_regions[normalized_input]
            return ValidationResult.valid(canonical_region, original_text)

        # Check aliases
        if normalized_input in self.region_aliases:
            canonical_region = self.region_aliases[normalized_input]
            return ValidationResult.valid(canonical_region, original_text)

        # Exact match against original regions (case-insensitive)
        for region in self.regions:
            if region.lower() == original_text.lower():
                return ValidationResult.valid(region, original_text)

        # Fuzzy matching for close matches
        suggestions = self._get_region_suggestions(normalized_input)

        if suggestions:
            # If we have a very close match (above fuzzy threshold), use it
            normalized_regions_list = list(self.normalized_regions.keys())
            close_matches = difflib.get_close_matches(
                normalized_input,
                normalized_regions_list,
                n=1,
                cutoff=self.fuzzy_match_threshold,
            )

            if close_matches:
                matched_normalized = close_matches[0]
                canonical_region = self.normalized_regions[matched_normalized]
                return ValidationResult.valid(canonical_region, original_text)

        # No direct match found, return suggestions
        return ValidationResult.invalid(
            f"Region '{original_text}' not recognized",
            original_value=original_text,
            suggestions=suggestions,
        )

    def _get_region_suggestions(self, normalized_input: str, max_suggestions: int = 3) -> List[str]:
        """
        Get region suggestions for invalid input.

        Args:
            normalized_input: Normalized input text
            max_suggestions: Maximum number of suggestions

        Returns:
            List[str]: List of suggested regions
        """
        if not normalized_input:
            return []

        suggestions = []

        # Get fuzzy matches from normalized regions
        normalized_regions_list = list(self.normalized_regions.keys())
        region_matches = difflib.get_close_matches(
            normalized_input,
            normalized_regions_list,
            n=max_suggestions,
            cutoff=self.suggestion_threshold,
        )

        # Convert back to canonical names
        for match in region_matches:
            canonical = self.normalized_regions[match]
            if canonical not in suggestions:
                suggestions.append(canonical)

        # Get fuzzy matches from aliases
        alias_keys = list(self.region_aliases.keys())
        alias_matches = difflib.get_close_matches(
            normalized_input,
            alias_keys,
            n=max_suggestions,
            cutoff=self.suggestion_threshold,
        )

        # Convert aliases to canonical names
        for alias in alias_matches:
            canonical = self.region_aliases[alias]
            if canonical not in suggestions:
                suggestions.append(canonical)

        return suggestions[:max_suggestions]

    def validate_message(self, message_text: str) -> ValidationResult:
        """
        Comprehensive message validation.

        Args:
            message_text: Message to validate

        Returns:
            ValidationResult: Comprehensive validation result
        """
        if not message_text:
            return ValidationResult.invalid("Please send me a message")

        # Sanitize first
        sanitized = self.sanitize_input(message_text)

        # Check length
        length_result = self.validate_message_length(sanitized)
        if not length_result.is_valid:
            return length_result

        # Check for spam
        spam_result = self.detect_spam(sanitized)
        if not spam_result.is_valid:
            return spam_result

        return ValidationResult.valid(sanitized, message_text)

    def get_validation_stats(self) -> Dict[str, any]:
        """
        Get statistics about the validator configuration.

        Returns:
            Dict[str, any]: Validation statistics
        """
        return {
            "total_regions": len(self.regions),
            "normalized_mappings": len(self.normalized_regions),
            "aliases": len(self.region_aliases),
            "max_message_length": self.max_message_length,
            "fuzzy_match_threshold": self.fuzzy_match_threshold,
            "suggestion_threshold": self.suggestion_threshold,
            "regions_list": sorted(list(self.regions)),
        }

    def get_popular_regions(self, count: int = 5) -> List[str]:
        """
        Get a list of popular regions for suggestions.

        Args:
            count: Number of regions to return

        Returns:
            List[str]: List of popular region names
        """
        # For now, just return first N regions alphabetically
        # In a real implementation, this could be based on usage statistics
        return sorted(list(self.regions))[:count]

    def update_regions(self, new_regions: List[str]) -> None:
        """
        Update the list of valid regions.

        Args:
            new_regions: New list of region names
        """
        self.regions = set(new_regions)
        self.normalized_regions = {self._normalize_text(r): r for r in new_regions}
        self.region_aliases = self._build_region_aliases()

        self.logger.info(
            f"Updated regions: {len(self.regions)} regions, {len(self.region_aliases)} aliases"
        )
