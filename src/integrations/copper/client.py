import os
import requests
from typing import Any, Iterable
from src.integrations.copper.mapping import copper_person_to_incoming

def _get_credentials() -> dict[str, str]:
    api_key = os.environ.get("COPPER_API_KEY")
    user_email = os.environ.get("COPPER_USER_EMAIL")
    
    if not api_key:
        raise RuntimeError("Missing required environment variable: COPPER_API_KEY")
    if not user_email:
        raise RuntimeError("Missing required environment variable: COPPER_USER_EMAIL")
        
    return {
        "api_key": api_key,
        "user_email": user_email,
        "base_url": os.environ.get("COPPER_API_BASE", "https://api.copper.com/developer_api/v1")
    }

def _post(url: str, headers: dict, json_data: dict) -> list[dict[str, Any]]:
    """Indirection point for network calls to facilitate testing."""
    response = requests.post(url, headers=headers, json=json_data, timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"Copper API error: {response.status_code} - {response.text} URL: {url}"
        )
    return response.json()

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Fetches all people from Copper and yields IncomingContact dicts.
    """
    creds = _get_credentials()
    url = f"{creds['base_url'].rstrip('/')}/people/search"
    
    headers = {
        "X-PW-AccessToken": creds["api_key"],
        "X-PW-Application": "developer_api",
        "X-PW-UserEmail": creds["user_email"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    page_number = 1
    page_size = 100

    while True:
        payload = {
            "page_size": page_size,
            "page_number": page_number,
            "sort_by": "name"
        }
        
        data = _post(url, headers, payload)
        
        if not data:
            break

        for record in data:
            yield copper_person_to_incoming(record)

        page_number += 1