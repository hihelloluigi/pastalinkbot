import os
import json
import requests
from typing import Dict, Any, Optional, Generator
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = (
    "You are a classifier for an Italian public services Telegram bot. "
    "Given a user message, respond with JSON ONLY in this exact schema:\n"
    "{\"intent\":\"...\", \"region\":null or \"<Italian region>\", \"confidence\":0..1, \"needs_region\":true|false}\n"
    "Allowed intents: fascicolo_sanitario, bollo_auto, patente, servizi_pubblici, anagrafe, cup, scuola, tari, "
    "greeting, smalltalk, help, about, off_topic, unknown.\n"
    "Rules:\n"
    "- 'cosa sai fare', 'help', 'aiuto', 'come funzioni' => intent=help\n"
    "- 'chi sei', 'chi ti ha creato', 'info bot' => intent=about\n"
    "- Greetings like 'ciao', 'hey', 'buongiorno' => intent=greeting\n"
    "- Small talk like 'come va' => intent=smalltalk\n"
    "- Region: valid Italian region name or null.\n"
    "- needs_region=true only for fascicolo_sanitario, bollo_auto, cup if region is missing.\n"
    "- off_topic for anything not related to Italian PA.\n"
    "- Respond with JSON only. No extra text.\n"
    "Examples:\n"
    "U: Cosa sai fare?\n"
    "A: {\"intent\":\"help\", \"region\":null, \"confidence\":0.95, \"needs_region\":false}\n"
    "U: Chi sei?\n"
    "A: {\"intent\":\"about\", \"region\":null, \"confidence\":0.95, \"needs_region\":false}\n"
    "U: Ciao\n"
    "A: {\"intent\":\"greeting\", \"region\":null, \"confidence\":0.95, \"needs_region\":false}\n"
    "U: Come va?\n"
    "A: {\"intent\":\"smalltalk\", \"region\":null, \"confidence\":0.95, \"needs_region\":false}\n"
)

def _post_chat(payload: Dict[str, Any], stream: bool = False):
    url = f"{OLLAMA_HOST}/api/chat"
    if stream:
        return requests.post(url, json=payload, stream=True, timeout=30)
    return requests.post(url, json=payload, timeout=30)

def classify(text: str) -> Dict[str, Any]:
    """Classify user text into intent/region using Ollama (non-streaming for reliability)."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "stream": False,
        "options": {"temperature": 0.0}
    }
    try:
        r = _post_chat(payload, stream=False)
        r.raise_for_status()
        content = r.json()["message"]["content"].strip()
        start = content.find("{"); end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found in response")
        data = json.loads(content[start:end+1])
        data.setdefault("intent", "unknown")
        data.setdefault("region", None)
        data.setdefault("confidence", 0.0)
        data.setdefault("needs_region", False)
        return data
    except Exception:
        return {"intent": "unknown", "region": None, "confidence": 0.0, "needs_region": False}

def classify_stream(text: str) -> Generator[str, None, None]:
    """Stream raw chunks from Ollama (useful for debugging)."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "stream": True,
        "options": {"temperature": 0.0}
    }
    with _post_chat(payload, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield line
