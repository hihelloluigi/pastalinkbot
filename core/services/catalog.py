"""
Catalog Management Service

This module handles loading, indexing, and querying the catalog of public service links.
It provides efficient lookups and caching for better performance.

Classes:
    CatalogService: Main service for catalog operations
    CatalogIndex: Efficient indexed access to catalog data
"""

import json
import logging
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config.constants import NATIONAL_REGION
from core.models.intent import CatalogEntry, IntentStats
from utils.logging import LoggerMixin, log_performance

logger = logging.getLogger(__name__)


class CatalogService(LoggerMixin):
    """
    Main service for catalog operations.

    This service handles loading, validating, and querying the catalog
    of public service links. It provides a high-level interface for
    all catalog-related operations.
    """

    def __init__(self, data_path: str, max_links_per_response: int = 6):
        """
        Initialize catalog service.

        Args:
            data_path: Path to catalog JSON file
            max_links_per_response: Maximum links to return per query
        """
        self.data_path = Path(data_path)
        self.max_links_per_response = max_links_per_response
        self.entries: List[CatalogEntry] = []
        self.index: Optional[CatalogIndex] = None
        self.stats: Dict[str, IntentStats] = {}

        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load and validate catalog from JSON file."""
        with log_performance("load_catalog", self.logger):
            try:
                if not self.data_path.exists():
                    self.logger.error(f"Catalog file not found: {self.data_path}")
                    self.entries = []
                    self._build_index()
                    return

                with open(self.data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                self.entries = self._validate_and_convert_entries(raw_data)
                self._build_index()

                self.logger.info(f"Successfully loaded {len(self.entries)} catalog entries")

            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in catalog file: {e}")
                self.entries = []
                self._build_index()
            except Exception as e:
                self.logger.error(f"Unexpected error loading catalog: {e}")
                self.entries = []
                self._build_index()

    def _validate_and_convert_entries(self, raw_data: List[Dict[str, Any]]) -> List[CatalogEntry]:
        """
        Validate and convert raw JSON data to CatalogEntry objects.

        Args:
            raw_data: Raw data from JSON file

        Returns:
            List[CatalogEntry]: Valid catalog entries
        """
        if not isinstance(raw_data, list):
            raise ValueError("Catalog data must be a list")

        valid_entries = []
        errors = 0

        for i, raw_entry in enumerate(raw_data):
            try:
                if not isinstance(raw_entry, dict):
                    self.logger.warning(f"Entry {i} is not a dictionary, skipping")
                    errors += 1
                    continue

                # Convert to CatalogEntry with validation
                entry = CatalogEntry.from_dict(raw_entry)
                valid_entries.append(entry)

            except Exception as e:
                self.logger.warning(f"Invalid entry {i}: {e}")
                errors += 1
                continue

        if errors > 0:
            self.logger.warning(f"Skipped {errors} invalid entries out of {len(raw_data)}")

        return valid_entries

    def _build_index(self) -> None:
        """Build search index from loaded entries."""
        try:
            self.index = CatalogIndex(self.entries)
        except Exception as e:
            self.logger.error(f"Failed to build catalog index: {e}")
            self.index = CatalogIndex([])  # Empty index as fallback

    def get_links(self, intent: str, region: Optional[str] = None) -> List[CatalogEntry]:
        """
        Get links for a specific intent and region.

        Args:
            intent: Intent to search for
            region: Optional region to filter by

        Returns:
            List[CatalogEntry]: Matching catalog entries, limited by max_links_per_response
        """
        if not self.index:
            self.logger.warning("Catalog index not available")
            return []

        try:
            # Get entries from index
            entries_tuple = self.index.get_entries(intent, region)
            entries_list = list(entries_tuple)

            # Apply fallback logic if no region-specific results
            if not entries_list and region:
                entries_tuple = self.index.get_entries(intent, None)
                entries_list = list(entries_tuple)

            # Limit results
            limited_entries = entries_list[: self.max_links_per_response]

            # Update statistics
            self._update_stats(intent, len(limited_entries) > 0, region)

            self.logger.debug(
                f"Found {len(limited_entries)} links for intent={intent}, region={region}"
            )

            return limited_entries

        except Exception as e:
            self.logger.error(f"Error getting links: {e}")
            self._update_stats(intent, False, region)
            return []

    def _update_stats(self, intent: str, success: bool, region: Optional[str] = None) -> None:
        """Update usage statistics."""
        try:
            if intent not in self.stats:
                self.stats[intent] = IntentStats(intent=intent)

            self.stats[intent].add_request(success=success, region=region)

        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")

    def get_regions(self) -> List[str]:
        """Get list of available regions."""
        if not self.index:
            return []
        return self.index.get_regions()

    def get_intents(self) -> List[str]:
        """Get list of available intents."""
        if not self.index:
            return []
        return self.index.get_intents()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about catalog usage.

        Returns:
            Dict[str, Any]: Statistics including index stats and usage stats
        """
        index_stats = self.index.get_stats() if self.index else {}

        usage_stats = {}
        for intent, stats in self.stats.items():
            usage_stats[intent] = stats.to_dict()

        return {
            "index": index_stats,
            "usage": usage_stats,
            "catalog_info": {
                "file_path": str(self.data_path),
                "file_exists": self.data_path.exists(),
                "max_links_per_response": self.max_links_per_response,
            },
        }

    def reload_catalog(self) -> bool:
        """
        Reload catalog from file.

        Returns:
            bool: True if reload was successful, False otherwise
        """
        try:
            self.logger.info("Reloading catalog from file")

            # Clear existing data
            self.entries = []
            if self.index:
                self.index.clear_cache()

            # Reload
            self._load_catalog()

            self.logger.info("Catalog reloaded successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reload catalog: {e}")
            return False

    def validate_catalog(self) -> Dict[str, Any]:
        """
        Validate catalog integrity and return validation report.

        Returns:
            Dict[str, Any]: Validation report with errors and warnings
        """
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "total_entries": len(self.entries),
            "intents_coverage": {},
            "regions_coverage": {},
        }

        try:
            # Check for duplicate entries
            seen_combinations = set()
            for i, entry in enumerate(self.entries):
                combination = (entry.intent, entry.region, entry.url)
                if combination in seen_combinations:
                    report["warnings"].append(f"Duplicate entry at index {i}: {combination}")
                seen_combinations.add(combination)

            # Check intent coverage
            intents = self.get_intents()
            for intent in intents:
                national_entries = len(
                    [e for e in self.entries if e.intent == intent and e.is_national]
                )
                regional_entries = len(
                    [e for e in self.entries if e.intent == intent and not e.is_national]
                )

                report["intents_coverage"][intent] = {
                    "national": national_entries,
                    "regional": regional_entries,
                    "total": national_entries + regional_entries,
                }

                if national_entries == 0 and regional_entries == 0:
                    report["errors"].append(f"Intent '{intent}' has no entries")
                    report["valid"] = False

            # Check region coverage
            regions = self.get_regions()
            for region in regions:
                region_entries = len([e for e in self.entries if e.region == region])
                report["regions_coverage"][region] = region_entries

                if region_entries == 0:
                    report["warnings"].append(f"Region '{region}' has no entries")

            # Check URL accessibility (basic validation)
            invalid_urls = []
            for entry in self.entries:
                if not (entry.url.startswith("http://") or entry.url.startswith("https://")):
                    invalid_urls.append(entry.url)

            if invalid_urls:
                report["warnings"].extend([f"Invalid URL format: {url}" for url in invalid_urls])

            if report["errors"]:
                report["valid"] = False

        except Exception as e:
            report["valid"] = False
            report["errors"].append(f"Validation failed: {e}")

        return report

    @property
    def is_empty(self) -> bool:
        """Check if catalog is empty."""
        return len(self.entries) == 0

    @property
    def entry_count(self) -> int:
        """Get number of entries in catalog."""
        return len(self.entries)


class CatalogIndex(LoggerMixin):
    """
    Efficient indexed access to catalog data with caching.

    This class builds and maintains search indexes for fast lookups
    of catalog entries by intent and region combinations.
    """

    def __init__(self, entries: List[CatalogEntry]):
        """
        Initialize catalog index with entries.

        Args:
            entries: List of catalog entries to index
        """
        self.entries = entries
        self.intent_index: Dict[str, List[CatalogEntry]] = defaultdict(list)
        self.region_index: Dict[str, List[CatalogEntry]] = defaultdict(list)
        self.intent_region_index: Dict[str, List[CatalogEntry]] = defaultdict(list)
        self.regions: Set[str] = set()
        self.intents: Set[str] = set()

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build search indexes for fast lookups."""
        with log_performance("build_catalog_indexes", self.logger):
            try:
                for entry in self.entries:
                    if not isinstance(entry, CatalogEntry):
                        self.logger.warning(f"Invalid entry type: {type(entry)}")
                        continue

                    intent = entry.intent
                    region = entry.region

                    # Intent-only index
                    if intent:
                        self.intent_index[intent].append(entry)
                        self.intents.add(intent)

                    # Region-only index
                    if region:
                        self.region_index[region].append(entry)
                        if region != NATIONAL_REGION:
                            self.regions.add(region)

                    # Combined intent+region index for fastest lookups
                    if intent and region:
                        key = self._make_combined_key(intent, region)
                        self.intent_region_index[key].append(entry)

                self.logger.info(
                    f"Built catalog indexes: {len(self.intent_index)} intents, "
                    f"{len(self.regions)} regions, {len(self.entries)} total entries"
                )

            except Exception as e:
                self.logger.error(f"Error building catalog indexes: {e}")
                raise

    def _make_combined_key(self, intent: str, region: str) -> str:
        """Create a combined key for intent+region lookups."""
        return f"{intent}|{region}"

    @lru_cache(maxsize=500)
    def get_entries(self, intent: str, region: Optional[str] = None) -> Tuple[CatalogEntry, ...]:
        """
        Get catalog entries with caching. Returns tuple for hashability.

        Args:
            intent: Intent to search for
            region: Optional region to filter by

        Returns:
            Tuple[CatalogEntry, ...]: Matching catalog entries
        """
        try:
            if not intent:
                return tuple()

            intent = intent.lower()

            # Try exact match first (intent + region)
            if region:
                key = self._make_combined_key(intent, region)
                if key in self.intent_region_index:
                    return tuple(self.intent_region_index[key])

            # Try national fallback
            national_key = self._make_combined_key(intent, NATIONAL_REGION)
            if national_key in self.intent_region_index:
                return tuple(self.intent_region_index[national_key])

            # Last resort: filter intent-only index
            if intent in self.intent_index:
                results = []
                for entry in self.intent_index[intent]:
                    if region and entry.region == region:
                        results.append(entry)
                    elif not region and entry.region == NATIONAL_REGION:
                        results.append(entry)

                return tuple(results)

            return tuple()

        except Exception as e:
            self.logger.error(f"Error getting entries for intent={intent}, region={region}: {e}")
            return tuple()

    def get_regions(self) -> List[str]:
        """Get list of available regions (excluding national)."""
        return sorted(self.regions)

    def get_intents(self) -> List[str]:
        """Get list of available intents."""
        return sorted(self.intents)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        cache_info = self.get_entries.cache_info()
        return {
            "total_entries": len(self.entries),
            "intents": len(self.intents),
            "regions": len(self.regions),
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize,
        }
