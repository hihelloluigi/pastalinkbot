"""
Classification Service

This module provides LLM-based intent classification with caching and error handling.
It integrates your existing Ollama LLM code with the new modular architecture.

Classes:
    ClassificationService: Main service for intent classification
"""

import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Generator, Optional

import requests
from dotenv import load_dotenv

from core.models.intent import ClassificationResult
from utils.decorators import retry
from utils.logging import LoggerMixin, log_performance

load_dotenv()

logger = logging.getLogger(__name__)


class ClassificationService(LoggerMixin):
    """
    LLM-based intent classification service.

    This service wraps your existing Ollama LLM functionality with
    enhanced error handling, caching, and async support.
    """

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model: Optional[str] = None,
        cache_size: int = 1000,
        timeout: int = 30,
    ):
        """
        Initialize classification service.

        Args:
            ollama_host: Ollama API host URL
            model: Model name to use
            cache_size: LRU cache size for classifications
            timeout: Request timeout in seconds
        """
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.timeout = timeout

        # Configure caching
        self._cached_classify = lru_cache(maxsize=cache_size)(self._classify_internal)

        # System prompt for classification
        self.system_prompt = self._build_system_prompt()

        self.logger.info(f"Classification service initialized with model: {self.model}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for classification."""
        return (
            "You are a classifier for an Italian public services Telegram bot. "
            "Given a user message, respond with JSON ONLY in this exact schema:\n"
            '{"intent":"...", "region":null or "<Italian region>", "confidence":0..1, "needs_region":true|false}\n'
            "Allowed intents: fascicolo_sanitario, bollo_auto, patente, cup, anpr, io_app, pagopa, scuola, tari, "
            "spid, cie, inps, agenzia_entrate, greeting, smalltalk, help, about, off_topic, unknown.\n"
            "Rules:\n"
            "- 'cosa sai fare', 'help', 'aiuto', 'come funzioni' => intent=help\n"
            "- 'chi sei', 'chi ti ha creato', 'info bot' => intent=about\n"
            "- Greetings like 'ciao', 'hey', 'buongiorno' => intent=greeting\n"
            "- Small talk like 'come va' => intent=smalltalk\n"
            "- Health records, medical records, FSE => intent=fascicolo_sanitario\n"
            "- Car tax, bollo auto, vehicle tax => intent=bollo_auto\n"
            "- Medical appointments, CUP, book visit => intent=cup\n"
            "- Driving license, patente => intent=patente\n"
            "- Certificates, anagrafe, ANPR => intent=anpr\n"
            "- IO app, app IO => intent=io_app\n"
            "- PagoPA, payments => intent=pagopa\n"
            "- School, scuola, iscrizioni => intent=scuola\n"
            "- Waste tax, TARI, tassa rifiuti => intent=tari\n"
            "- SPID, identità digitale => intent=spid\n"
            "- CIE, carta identità elettronica => intent=cie\n"
            "- INPS, pensioni, social security => intent=inps\n"
            "- Agenzia Entrate, tasse, fiscale => intent=agenzia_entrate\n"
            "- Region: valid Italian region name or null.\n"
            "- needs_region=true only for fascicolo_sanitario, bollo_auto, cup if region is missing.\n"
            "- off_topic for anything not related to Italian PA.\n"
            "- Respond with JSON only. No extra text.\n"
            "Examples:\n"
            "U: Cosa sai fare?\n"
            'A: {"intent":"help", "region":null, "confidence":0.95, "needs_region":false}\n'
            "U: Come richiedere SPID?\n"
            'A: {"intent":"spid", "region":null, "confidence":0.9, "needs_region":false}\n'
            "U: Prenotare visita medica in Lombardia\n"
            'A: {"intent":"cup", "region":"Lombardia", "confidence":0.9, "needs_region":false}\n'
            "U: Fascicolo sanitario\n"
            'A: {"intent":"fascicolo_sanitario", "region":null, "confidence":0.9, "needs_region":true}\n'
        )

    @retry(max_attempts=3, delay_seconds=1.0, exceptions=(requests.RequestException,))
    def _post_chat(self, payload: Dict[str, Any], stream: bool = False):
        """Make HTTP request to Ollama API with retry logic."""
        url = f"{self.ollama_host}/api/chat"

        if stream:
            return requests.post(url, json=payload, stream=True, timeout=self.timeout)
        return requests.post(url, json=payload, timeout=self.timeout)

    def _classify_internal(self, text_hash: str, text: str) -> str:
        """
        Internal classification method for caching.

        Args:
            text_hash: Hash of the text for caching
            text: Original text to classify

        Returns:
            str: JSON string of classification result
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            with log_performance(f"llm_classification", self.logger):
                response = self._post_chat(payload, stream=False)
                response.raise_for_status()

                content = response.json()["message"]["content"].strip()

                # Extract JSON from response
                start = content.find("{")
                end = content.rfind("}")

                if start == -1 or end == -1:
                    raise ValueError("No JSON found in LLM response")

                json_str = content[start : end + 1]

                # Validate JSON
                data = json.loads(json_str)

                # Ensure required fields
                data.setdefault("intent", "unknown")
                data.setdefault("region", None)
                data.setdefault("confidence", 0.0)
                data.setdefault("needs_region", False)

                return json.dumps(data)

        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            # Return default classification
            default_result = {
                "intent": "unknown",
                "region": None,
                "confidence": 0.0,
                "needs_region": False,
            }
            return json.dumps(default_result)

    async def classify_async(self, text: str) -> ClassificationResult:
        """
        Classify text asynchronously.

        Args:
            text: Text to classify

        Returns:
            ClassificationResult: Classification result with validation
        """
        if not text or not text.strip():
            return ClassificationResult(
                intent="unknown", region=None, needs_region=False, confidence=0.0
            )

        try:
            # Create hash for caching
            text_hash = str(hash(text.lower().strip()[:100]))

            # Run classification in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result_json = await loop.run_in_executor(None, self._cached_classify, text_hash, text)

            # Parse result
            result_data = json.loads(result_json)

            # Create ClassificationResult with validation
            classification = ClassificationResult(
                intent=result_data.get("intent", "unknown"),
                region=result_data.get("region"),
                needs_region=result_data.get("needs_region", False),
                confidence=result_data.get("confidence", 0.0),
                raw_response=result_data,
            )

            self.logger.debug(f"Classified '{text[:50]}...' as {classification.intent}")
            return classification

        except Exception as e:
            self.logger.error(f"Async classification failed: {e}")
            return ClassificationResult(
                intent="unknown", region=None, needs_region=False, confidence=0.0
            )

    def classify_sync(self, text: str) -> ClassificationResult:
        """
        Classify text synchronously (for backward compatibility).

        Args:
            text: Text to classify

        Returns:
            ClassificationResult: Classification result
        """
        # Use asyncio to run the async version
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.classify_async(text))

    def classify_stream(self, text: str) -> Generator[str, None, None]:
        """
        Stream classification response (useful for debugging).

        Args:
            text: Text to classify

        Yields:
            str: Raw response chunks from LLM
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": True,
            "options": {"temperature": 0.0},
        }

        try:
            with self._post_chat(payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        yield line
        except Exception as e:
            self.logger.error(f"Stream classification failed: {e}")
            yield f'{{"error": "Classification failed: {str(e)}"}}'

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_info = self._cached_classify.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "maxsize": cache_info.maxsize,
            "currsize": cache_info.currsize,
            "hit_rate": (
                cache_info.hits / (cache_info.hits + cache_info.misses)
                if (cache_info.hits + cache_info.misses) > 0
                else 0.0
            ),
        }

    def clear_cache(self) -> None:
        """Clear the classification cache."""
        self._cached_classify.cache_clear()
        self.logger.info("Classification cache cleared")

    def health_check(self) -> Dict[str, Any]:
        """
        Check if the LLM service is healthy.

        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Try a simple classification
            test_result = self.classify_sync("test")

            return {
                "status": "healthy",
                "model": self.model,
                "host": self.ollama_host,
                "cache_stats": self.get_cache_stats(),
                "test_classification": test_result.intent != "unknown",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model,
                "host": self.ollama_host,
            }

    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update the system prompt and clear cache.

        Args:
            new_prompt: New system prompt to use
        """
        self.system_prompt = new_prompt
        self.clear_cache()
        self.logger.info("System prompt updated and cache cleared")


# Backward compatibility: provide the same interface as your original llm.py
def classify(text: str) -> Dict[str, Any]:
    """
    Backward compatibility function for your existing code.

    Args:
        text: Text to classify

    Returns:
        Dict[str, Any]: Classification result in original format
    """
    # Create a default service instance
    service = ClassificationService()
    result = service.classify_sync(text)

    # Convert to original format
    return {
        "intent": result.intent,
        "region": result.region,
        "confidence": result.confidence,
        "needs_region": result.needs_region,
    }
