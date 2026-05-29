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

def _get(url: str, api_key: str, params: dict) -> dict:
    """Performs a GET request to the Close API with Basic Auth."""
    response = requests.get(
        url,
        auth=(api_key, ""),
        params=params,
        timeout=30
    )
    if not (200 <= response.status_code < 300):
        raise RuntimeError(
            f"Close API request failed with status {response.status_code}. "
            f"URL: {url}, Response: {response.text}"
        )
    return response.json()

def fetch_contacts() -> List[Dict[str, Any]]:
    """
    Discovers and returns all contacts from Close.com.
    """
    api_key, base_url = _get_credentials()
    contacts_url = f"{base_url}/contact/"
    
    all_contacts = []
    skip = 0
    limit = 100
    has_more = True
    
    while has_more:
        params = {"_skip": skip, "_limit": limit}
        page_data = _get(contacts_url, api_key, params)
        
        data = page_data.get("data", [])
        if not data:
            break
            
        for record in data:
            all_contacts.append(close_contact_to_incoming(record))
            
        has_more = page_data.get("has_more", False)
        if has_more:
            skip += len(data)
            
    return all_contacts