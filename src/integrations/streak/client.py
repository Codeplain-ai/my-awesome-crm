import os
import requests
from typing import Any, Dict, List, Iterable
from src.integrations.streak.mapping import streak_contact_to_incoming

def _get(url: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Indirection point for HTTP GET requests to Streak.
    """
    response = requests.get(url, auth=(api_key, ""), timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"Streak API request failed: {response.status_code} - {response.text} URL: {url}"
        )
    return response.json()

def fetch_contacts() -> Iterable[Dict[str, Any]]:
    """
    Fetches all contacts from Streak and yields IncomingContact dicts.
    """
    api_key = os.environ.get("STREAK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: STREAK_API_KEY")

    api_base = os.environ.get("STREAK_API_BASE", "https://www.streak.com/api/v2").rstrip("/")
    url = f"{api_base}/contacts"

    # Streak v2 /contacts returns a list directly
    records = _get(url, api_key)
    
    for record in records:
        yield streak_contact_to_incoming(record)