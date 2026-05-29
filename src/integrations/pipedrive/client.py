import os
import requests
from typing import Any
from src.integrations.pipedrive.mapping import pipedrive_person_to_incoming

def _get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable for Pipedrive: {key}")
    return val

def _request_page(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Indirection point for HTTP calls to facilitate mocking."""
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        try:
            error_msg = response.json().get("error", response.text)
        except Exception:
            error_msg = response.text
        raise RuntimeError(f"Pipedrive API error (Status {response.status_code}): {error_msg}")
    return response.json()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Discovery entry point. Fetches all persons from Pipedrive.
    """
    api_token = _get_env("PIPEDRIVE_API_TOKEN")
    domain = _get_env("PIPEDRIVE_COMPANY_DOMAIN")
    
    base_url = f"https://{domain}.pipedrive.com/v1/persons"
    
    contacts = []
    start = 0
    limit = 100
    
    while True:
        params = {
            "api_token": api_token,
            "start": start,
            "limit": limit
        }
        
        data = _request_page(base_url, params)
        
        person_list = data.get("data") or []
        for person in person_list:
            contacts.append(pipedrive_person_to_incoming(person))
            
        # Pipedrive pagination check
        pagination = data.get("additional_data", {}).get("pagination", {})
        more_items = pagination.get("more_items_in_collection", False)
        
        if more_items:
            start = pagination.get("next_start")
            if start is None:
                break
        else:
            break
            
    return contacts