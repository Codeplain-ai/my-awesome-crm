import os
import requests
from typing import Any
from src.integrations.sugarcrm.mapping import sugarcrm_contact_to_incoming

def _token_exchange(api_base: str, client_id: str, client_secret: str, username: str, password: str, platform: str) -> str:
    """Performs OAuth2 token exchange with SugarCRM."""
    url = f"{api_base}/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "platform": platform,
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        raise RuntimeError(f"SugarCRM auth failed ({response.status_code}) at {url}: {response.text}")
    
    try:
        return response.json()["access_token"]
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"SugarCRM auth response missing access_token: {str(e)}")

def _get_contacts_page(api_base: str, access_token: str, offset: int) -> dict[str, Any]:
    """Fetches a single page of contacts using the SugarCRM offset/max_num pattern."""
    url = f"{api_base}/Contacts"
    headers = {
        "OAuth-Token": access_token,
        "Accept": "application/json"
    }
    params = {"offset": offset, "max_num": 200}
    
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        raise RuntimeError(f"SugarCRM API call failed ({response.status_code}) at {url}: {response.text}")
    
    return response.json()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Orchestrates the fetching and mapping of SugarCRM contacts.
    """
    api_base = os.environ.get("SUGARCRM_API_BASE", "").rstrip("/")
    username = os.environ.get("SUGARCRM_USERNAME")
    password = os.environ.get("SUGARCRM_PASSWORD")
    
    if not api_base or not username or not password:
        missing = [k for k, v in {
            "SUGARCRM_API_BASE": api_base, 
            "SUGARCRM_USERNAME": username, 
            "SUGARCRM_PASSWORD": password
        }.items() if not v]
        raise RuntimeError(f"Missing required SugarCRM credentials: {', '.join(missing)}")

    client_id = os.environ.get("SUGARCRM_CLIENT_ID", "sugar")
    client_secret = os.environ.get("SUGARCRM_CLIENT_SECRET", "")
    platform = os.environ.get("SUGARCRM_PLATFORM", "base")

    token = _token_exchange(api_base, client_id, client_secret, username, password, platform)
    
    all_incoming_contacts = []
    offset = 0

    while True:
        data = _get_contacts_page(api_base, token, offset)
        records = data.get("records", [])
        
        if not records:
            break

        for record in records:
            all_incoming_contacts.append(sugarcrm_contact_to_incoming(record))

        next_offset = data.get("next_offset", -1)
        # SugarCRM convention: returns -1 when no more records exist
        if next_offset < 0:
            break
        
        # Prevent infinite loops if API behaves unexpectedly
        if next_offset == offset:
            break
            
        offset = next_offset
        
    return all_incoming_contacts