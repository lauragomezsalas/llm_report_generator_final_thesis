import os
import json
import time
import hashlib
import requests
from datetime import datetime

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
CACHE_DIR = "retrieval_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()


def _load_cache(hash_key: str):
    path = os.path.join(CACHE_DIR, f"{hash_key}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(hash_key: str, data: dict):
    path = os.path.join(CACHE_DIR, f"{hash_key}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _call_serper(query: str):
    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": 5
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def retrieve_external_context(structured_input: dict) -> dict:
    """
    External RAG Retrieval Layer
    """

    start_time = time.time()

    # Construct intelligent query
    query = " ".join([
        structured_input.get("market_analysis", ""),
        " ".join(structured_input.get("strategic_questions", []))
    ])

    hash_key = _hash_query(query)

    cached = _load_cache(hash_key)
    if cached:
        return {
            "query": query,
            "documents": cached["documents"],
            "cache_hit": True,
            "retrieval_latency": 0,
            "timestamp": cached["timestamp"]
        }

    # Live retrieval
    raw_results = _call_serper(query)

    documents = []

    for item in raw_results.get("organic", []):
        documents.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet")
        })

    retrieval_data = {
        "query": query,
        "documents": documents,
        "cache_hit": False,
        "retrieval_latency": round(time.time() - start_time, 4),
        "timestamp": datetime.utcnow().isoformat()
    }

    _save_cache(hash_key, retrieval_data)

    return retrieval_data


