"""
Intent Data Models

This module defines data models for handling intents and classification results.
These models provide type safety and validation for intent-related data.

Classes:
    ClassificationResult: Result of LLM intent classification
    IntentRequest: User request with classified intent
    IntentResponse: Response data for an intent
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config.constants import IntentType


@dataclass
class ClassificationResult:
    """
    Result of LLM intent classification.

    This class represents the output from the LLM classifier,
    including the detected intent, region, and whether additional
    region information is needed.

    Attributes:
        intent: Classified intent type
        region: Detected region (if any)
        needs_region: Whether the intent requires region specification
        confidence: Confidence score from classifier (0.0-1.0)
        raw_response: Raw response from LLM for debugging
    """

    intent: str
    region: Optional[str] = None
    needs_region: bool = False
    confidence: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate classification result after creation."""
        self._validate_intent()
        self._validate_confidence()
        self._validate_region_consistency()

    def _validate_intent(self) -> None:
        """Validate that intent is a known type."""
        if not self.intent:
            raise ValueError("Intent cannot be empty")

        # Convert to lowercase for consistency
        self.intent = self.intent.lower()

        # Check if it's a valid intent type
        valid_intents = [intent.value for intent in IntentType]
        if self.intent not in valid_intents:
            # Allow unknown intents but log warning
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown intent type: {self.intent}")

    def _validate_confidence(self) -> None:
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def _validate_region_consistency(self) -> None:
        """Validate region and needs_region consistency."""
        # If region is provided, needs_region should generally be False
        # (unless the LLM detected a region but it's invalid)
        if self.region and self.needs_region:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Region provided ({self.region}) but needs_region is True")

    @property
    def is_conversational(self) -> bool:
        """Check if this is a conversational intent."""
        return IntentType.is_conversational(self.intent)

    @property
    def requires_region(self) -> bool:
        """Check if this intent type requires a region."""
        return IntentType.requires_region(self.intent)

    @property
    def is_valid(self) -> bool:
        """Check if classification result is valid and actionable."""
        return (
            self.intent != IntentType.UNKNOWN.value
            and self.confidence > 0.1
            and (not self.requires_region or self.region or self.needs_region)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent,
            "region": self.region,
            "needs_region": self.needs_region,
            "confidence": self.confidence,
            "is_conversational": self.is_conversational,
            "requires_region": self.requires_region,
            "is_valid": self.is_valid,
        }


@dataclass
class IntentRequest:
    """
    User request with classified intent.

    This class represents a user's request after it has been
    processed and classified by the system.

    Attributes:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        message_text: Original user message
        classification: Classification result
        user_language: User's language code
        timestamp: Request timestamp
    """

    user_id: int
    chat_id: int
    message_text: str
    classification: ClassificationResult
    user_language: Optional[str] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            import time

            self.timestamp = time.time()

    @property
    def intent(self) -> str:
        """Get intent from classification."""
        return self.classification.intent

    @property
    def region(self) -> Optional[str]:
        """Get region from classification."""
        return self.classification.region

    @property
    def needs_region(self) -> bool:
        """Check if request needs region information."""
        return self.classification.needs_region

    def with_region(self, region: str) -> "IntentRequest":
        """Create a new IntentRequest with specified region."""
        new_classification = ClassificationResult(
            intent=self.classification.intent,
            region=region,
            needs_region=False,
            confidence=self.classification.confidence,
            raw_response=self.classification.raw_response,
        )

        return IntentRequest(
            user_id=self.user_id,
            chat_id=self.chat_id,
            message_text=self.message_text,
            classification=new_classification,
            user_language=self.user_language,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "message_text": self.message_text[:100],  # Truncate for privacy
            "classification": self.classification.to_dict(),
            "user_language": self.user_language,
            "timestamp": self.timestamp,
        }


@dataclass
class CatalogEntry:
    """
    Single entry in the catalog of links.

    Attributes:
        intent: Intent this entry serves
        region: Region this entry is for (or "Nazionale")
        label: Human-readable label for the link
        url: URL to the service
        description: Optional description
        tags: Optional tags for additional filtering
    """

    intent: str
    region: str
    label: str
    url: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    def __post_init__(self):
        """Validate catalog entry after creation."""
        self._validate_required_fields()
        self._validate_url()
        self._normalize_data()

    def _validate_required_fields(self) -> None:
        """Validate required fields are present."""
        if not self.intent:
            raise ValueError("Intent is required")
        if not self.region:
            raise ValueError("Region is required")
        if not self.label:
            raise ValueError("Label is required")
        if not self.url:
            raise ValueError("URL is required")

    def _validate_url(self) -> None:
        """Basic URL validation."""
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError(f"Invalid URL format: {self.url}")

    def _normalize_data(self) -> None:
        """Normalize data for consistency."""
        self.intent = self.intent.lower().strip()
        self.region = self.region.strip()
        self.label = self.label.strip()
        self.url = self.url.strip()

        if self.description:
            self.description = self.description.strip()

        if self.tags:
            self.tags = [tag.lower().strip() for tag in self.tags]

    @property
    def is_national(self) -> bool:
        """Check if this is a national-level service."""
        return self.region.lower() in ["nazionale", "national"]

    def matches_request(self, intent: str, region: Optional[str] = None) -> bool:
        """
        Check if this entry matches a request.

        Args:
            intent: Intent to match
            region: Region to match (optional)

        Returns:
            bool: True if this entry matches the request
        """
        if self.intent != intent.lower():
            return False

        if region:
            return self.region.lower() == region.lower()
        else:
            return self.is_national

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent,
            "region": self.region,
            "label": self.label,
            "url": self.url,
            "description": self.description,
            "tags": self.tags,
            "is_national": self.is_national,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogEntry":
        """Create CatalogEntry from dictionary."""
        return cls(
            intent=data["intent"],
            region=data["region"],
            label=data["label"],
            url=data["url"],
            description=data.get("description"),
            tags=data.get("tags"),
        )


@dataclass
class IntentStats:
    """
    Statistics for intent usage.

    Attributes:
        intent: Intent name
        total_requests: Total number of requests
        successful_responses: Number of successful responses
        failed_responses: Number of failed responses
        average_confidence: Average classification confidence
        regions_requested: List of regions requested for this intent
    """

    intent: str
    total_requests: int = 0
    successful_responses: int = 0
    failed_responses: int = 0
    average_confidence: float = 0.0
    regions_requested: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize regions list if not provided."""
        if self.regions_requested is None:
            self.regions_requested = []

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_responses / self.total_requests

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_responses / self.total_requests

    def add_request(
        self, success: bool, confidence: float = 0.0, region: Optional[str] = None
    ) -> None:
        """
        Add a request to the statistics.

        Args:
            success: Whether the request was successful
            confidence: Classification confidence
            region: Region requested (if any)
        """
        self.total_requests += 1

        if success:
            self.successful_responses += 1
        else:
            self.failed_responses += 1

        # Update average confidence
        if confidence > 0:
            old_avg = self.average_confidence
            self.average_confidence = (
                old_avg * (self.total_requests - 1) + confidence
            ) / self.total_requests

        # Track region
        if region and region not in self.regions_requested:
            self.regions_requested.append(region)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent,
            "total_requests": self.total_requests,
            "successful_responses": self.successful_responses,
            "failed_responses": self.failed_responses,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_confidence": self.average_confidence,
            "regions_requested": self.regions_requested,
        }
