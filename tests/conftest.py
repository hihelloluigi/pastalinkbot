"""
Pytest configuration and fixtures for PAstaLinkBot tests.

This module provides common fixtures and configuration for all tests.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from config.settings import Settings
from core.models.intent import CatalogEntry
from core.services.catalog import CatalogService
from core.services.classifier import ClassificationService
from core.services.formatter import ResponseFormatterService
from core.services.validator import InputValidationService, ValidationResult


@pytest.fixture
def sample_catalog_data() -> List[Dict[str, Any]]:
    """Sample catalog data for testing."""
    return [
        {
            "intent": "fascicolo_sanitario",
            "region": "Lombardia",
            "label": "FSE Lombardia",
            "url": "https://www.fascicolosanitario.regione.lombardia.it/",
            "description": "Accesso con SPID/CIE/CNS",
        },
        {
            "intent": "bollo_auto",
            "region": "Nazionale",
            "label": "Calcolo Bollo Auto",
            "url": "https://www.aci.it/servizi-online/bollo-auto",
            "description": "Calcolo bollo auto online",
        },
        {
            "intent": "patente",
            "region": "Nazionale",
            "label": "Rinnovo Patente",
            "url": "https://www.ilportaledellautomobilista.it/web/portale-automobilista/rinnovo-patente",
            "description": "Rinnovo patente di guida",
        },
        {
            "intent": "cup",
            "region": "Lazio",
            "label": "CUP Lazio",
            "url": "https://cup.regione.lazio.it/",
            "description": "Prenotazione visite specialistiche",
        },
    ]


@pytest.fixture
def sample_catalog_entries(sample_catalog_data) -> List[CatalogEntry]:
    """Sample catalog entries for testing."""
    return [CatalogEntry(**entry) for entry in sample_catalog_data]


@pytest.fixture
def temp_catalog_file(tmp_path, sample_catalog_data) -> Path:
    """Create a temporary catalog file for testing."""
    catalog_file = tmp_path / "test_catalog.json"
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(sample_catalog_data, f, ensure_ascii=False, indent=2)
    return catalog_file


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing."""
    return Settings(
        telegram_token="test_token_12345",
        data_path="./data/test_catalog.json",
        log_level="DEBUG",
        environment="test",
        max_message_length=1000,
        max_links_per_response=6,
        cache_size_links=100,
        cache_size_classifications=200,
        admin_user_ids=[123456789],
        fuzzy_match_threshold=0.7,
        suggestion_threshold=0.4,
        regions_per_message=15,
    )


@pytest.fixture
def catalog_service(temp_catalog_file) -> CatalogService:
    """Catalog service instance for testing."""
    return CatalogService(data_path=str(temp_catalog_file), max_links_per_response=6)


@pytest.fixture
def validation_service() -> InputValidationService:
    """Validation service instance for testing."""
    regions = ["Lombardia", "Lazio", "Toscana", "Veneto", "Piemonte", "Nazionale"]
    return InputValidationService(
        regions=regions,
        max_message_length=1000,
        fuzzy_match_threshold=0.7,
        suggestion_threshold=0.4,
    )


@pytest.fixture
def classifier_service() -> ClassificationService:
    """Classification service instance for testing."""
    return ClassificationService(
        ollama_host="http://localhost:11434",
        model="llama3.1:8b",
        cache_size=100,
        timeout=30,
    )


@pytest.fixture
def formatter_service() -> ResponseFormatterService:
    """Response formatter service instance for testing."""
    return ResponseFormatterService(max_links=6, regions_per_message=15)


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update object."""
    update = Mock()
    update.message = Mock()
    update.message.text = "test message"
    update.message.from_user = Mock()
    update.message.from_user.id = 123456789
    update.message.from_user.language_code = "it"
    update.message.chat = Mock()
    update.message.chat.id = 987654321
    return update


@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context object."""
    context = Mock()
    context.bot = Mock()
    context.bot.send_message = Mock()
    context.bot.send_chat_action = Mock()
    return context


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "model": "llama3.1:8b",
        "created_at": "2024-01-01T00:00:00Z",
        "response": '{"intent":"fascicolo_sanitario","region":"Lombardia","confidence":0.9,"needs_region":false}',
        "done": True,
    }


@pytest.fixture
def sample_regions() -> List[str]:
    """Sample list of Italian regions for testing."""
    return [
        "Abruzzo",
        "Basilicata",
        "Calabria",
        "Campania",
        "Emilia-Romagna",
        "Friuli-Venezia Giulia",
        "Lazio",
        "Liguria",
        "Lombardia",
        "Marche",
        "Molise",
        "Piemonte",
        "Puglia",
        "Sardegna",
        "Sicilia",
        "Toscana",
        "Trentino-Alto Adige",
        "Umbria",
        "Valle d'Aosta",
        "Veneto",
        "Nazionale",
    ]


@pytest.fixture
def sample_classification_results() -> List[Dict[str, Any]]:
    """Sample classification results for testing."""
    return [
        {
            "intent": "fascicolo_sanitario",
            "region": "Lombardia",
            "confidence": 0.95,
            "needs_region": False,
        },
        {
            "intent": "bollo_auto",
            "region": None,
            "confidence": 0.88,
            "needs_region": True,
        },
        {
            "intent": "greeting",
            "region": None,
            "confidence": 0.92,
            "needs_region": False,
        },
        {"intent": "help", "region": None, "confidence": 0.98, "needs_region": False},
    ]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        if "test_" in item.nodeid:
            if "integration" in item.nodeid:
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)
