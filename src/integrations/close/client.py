import os
import requests
from typing import Any, Dict, Iterable, List
from .mapping import close_contact_to_incoming

def _get_credentials() -> tuple[str, str]:
    """Reads Close credentials from environment variables."""
    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: CLOSE_API_KEY")
    
    base_url = os.environ.get("CLOSE_API_BASE", "https://api.close.com/api/v1")
    return api_key, base_url.rstrip("/")

def _fetch_page(api_key: str, url: str, skip: int) -> Dict[str, Any]:
    """Performs the actual HTTP request to Close API."""
    response = requests.get(
        f"{url}/contact/",
        auth=(api_key, ""),
        params={"_skip": skip},
        timeout=30
    )
    if not response.ok:
        raise RuntimeError(
            f"Close API request failed with status {response.status_code}: {response.text}"
        )
    return response.json()

def fetch_contacts() -> Iterable[Dict[str, Any]]:
    """
    Discovers and yields all contacts from Close.com.
    """
    api_key, base_url = _get_credentials()
    
    skip = 0
    has_more = True
    
    while has_more:
        data = _fetch_page(api_key, base_url, skip)
        records: List[Dict[str, Any]] = data.get("data", [])
        
        for record in records:
            yield close_contact_to_incoming(record)
            
        has_more = data.get("has_more", False)
        if has_more:
            skip += len(records)