import os
import requests
from typing import Generator, Any
from src.integrations.nimble.mapping import nimble_contact_to_incoming

def _get(url: str, headers: dict, params: dict) -> dict:
    """
    Indirection point for HTTP GET requests to allow testing.
    """
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"Nimble API error: {response.status_code} - {response.text} for URL: {url}"
        )
    return response.json()

def fetch_contacts() -> Generator[dict[str, Any], None, None]:
    """
    Reads Nimble credentials, pages through contacts, and yields IncomingContact dicts.
    """
    access_token = os.environ.get("NIMBLE_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Missing required environment variable: NIMBLE_ACCESS_TOKEN")

    api_base = os.environ.get("NIMBLE_API_BASE", "https://api.nimble.com/api/v1").rstrip("/")
    url = f"{api_base}/contacts"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    limit = 100
    offset = 0

    while True:
        params = {
            "record_type": "person",
            "limit": limit,
            "offset": offset
        }
        
        data = _get(url, headers, params)
        resources = data.get("resources", [])
        
        if not resources:
            break

        for record in resources:
            yield nimble_contact_to_incoming(record)

        # Nimble v1 uses offset/limit. Check if we might have more.
        # Based on typical API behavior; if we got a full page, request the next.
        if len(resources) < limit:
            break
            
        offset += limit