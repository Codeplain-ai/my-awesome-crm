import os
import requests
from typing import Any
from src.integrations.pipedrive.mapping import pipedrive_person_to_incoming

def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Indirection point for HTTP GET requests.
    Raises RuntimeError on non-2xx response with status and body.
    """
    resp = requests.get(url, params=params, timeout=30)
    if not resp.ok:
        raise RuntimeError(
            f"Pipedrive API request failed with status {resp.status_code}: {resp.text}"
        )
    return resp.json()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Discovery entry point. Fetches all persons from Pipedrive using start/limit pagination.
    """
    api_token = os.environ.get("PIPEDRIVE_API_TOKEN")
    if not api_token:
        raise RuntimeError("Missing required environment variable: PIPEDRIVE_API_TOKEN")
    
    domain = os.environ.get("PIPEDRIVE_COMPANY_DOMAIN")
    if not domain:
        raise RuntimeError("Missing required environment variable: PIPEDRIVE_COMPANY_DOMAIN")
    
    url = f"https://{domain}.pipedrive.com/v1/persons"
    contacts = []
    start = 0
    limit = 100
    
    while True:
        params = {
            "api_token": api_token,
            "start": start,
            "limit": limit
        }
        
        body = _get(url, params)
        data = body.get("data")
        
        if not data:
            break
            
        for person in data:
            contacts.append(pipedrive_person_to_incoming(person))
            
        pagination = body.get("additional_data", {}).get("pagination", {})
        more_items = pagination.get("more_items_in_collection", False)
        next_start = pagination.get("next_start")
        
        if more_items and next_start is not None:
            start = next_start
        else:
            break
            
    return contacts