import os
import requests
from typing import Generator, Any
from src.integrations.nimble.mapping import nimble_contact_to_incoming

def _get(url: str, access_token: str, params: dict) -> dict:
    """
    Indirection point for HTTP GET requests to allow testing.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"Nimble API error: {response.status_code} - {url} - {response.text}"
        )
    return response.json()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Reads Nimble credentials, pages through contacts, and returns a list of IncomingContact dicts.
    """
    access_token = os.environ.get("NIMBLE_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Missing required environment variable: NIMBLE_ACCESS_TOKEN")

    api_base = os.environ.get("NIMBLE_API_BASE", "https://api.nimble.com/api/v1").rstrip("/")
    url = f"{api_base}/contacts"
    
    contacts = []
    page = 1
    per_page = 100

    while True:
        params = {
            "record_type": "person",
            "page": page,
            "per_page": per_page
        }
        
        data = _get(url, access_token, params)
        resources = data.get("resources", [])
        meta = data.get("meta", {})
        
        if not resources:
            break

        for record in resources:
            contacts.append(nimble_contact_to_incoming(record))

        total_pages = meta.get("pages", 1)
        current_page = meta.get("page", 1)

        if current_page >= total_pages:
            break
            
        page += 1
    
    return contacts