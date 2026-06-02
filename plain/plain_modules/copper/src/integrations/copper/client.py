import os
import requests
from typing import Any, Iterable
from src.integrations.copper.mapping import copper_person_to_incoming

def _get_credentials() -> dict[str, str]:
    """Reads Copper credentials from environment variables."""
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

def _search(url: str, api_key: str, user_email: str, body: dict) -> list[dict[str, Any]]:
    """
    Indirection point for Copper Search API calls.
    Performs a POST request and returns the resulting JSON array.
    """
    headers = {
        "X-PW-AccessToken": api_key,
        "X-PW-Application": "developer_api",
        "X-PW-UserEmail": user_email,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    response = requests.post(url, headers=headers, json=body, timeout=30)
    
    if not (200 <= response.status_code < 300):
        raise RuntimeError(
            f"Copper API error: {response.status_code} - {response.text} "
            f"URL: {url} Body: {body}"
        )
        
    data = response.json()
    if not isinstance(data, list):
        # Copper /people/search returns a JSON array
        return []
    return data

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Fetches all people from Copper using pagination and yields IncomingContact dicts.
    """
    creds = _get_credentials()
    url = f"{creds['base_url'].rstrip('/')}/people/search"
    
    page_number = 1
    page_size = 200  # Default size as per requirements

    while True:
        body = {
            "page_size": page_size,
            "page_number": page_number,
            "sort_by": "name"
        }
        
        records = _search(
            url=url, 
            api_key=creds["api_key"], 
            user_email=creds["user_email"], 
            body=body
        )
        
        if not records:
            break

        for record in records:
            yield copper_person_to_incoming(record)

        # Stop if we received fewer items than requested (end of data)
        if len(records) < page_size:
            break

        page_number += 1