import os
import requests
from typing import Generator, Any
from src.integrations.sugarcrm.mapping import sugarcrm_contact_to_incoming

def _authenticate() -> str:
    """Performs OAuth2 token exchange."""
    base_url = os.environ.get("SUGARCRM_API_BASE", "").rstrip("/")
    username = os.environ.get("SUGARCRM_USERNAME")
    password = os.environ.get("SUGARCRM_PASSWORD")
    
    if not base_url or not username or not password:
        missing = [k for k, v in {
            "SUGARCRM_API_BASE": base_url, 
            "SUGARCRM_USERNAME": username, 
            "SUGARCRM_PASSWORD": password
        }.items() if not v]
        raise RuntimeError(f"Missing required SugarCRM credentials: {', '.join(missing)}")

    client_id = os.environ.get("SUGARCRM_CLIENT_ID", "sugar")
    client_secret = os.environ.get("SUGARCRM_CLIENT_SECRET", "")
    platform = os.environ.get("SUGARCRM_PLATFORM", "base")

    token_url = f"{base_url}/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "platform": platform,
    }

    response = requests.post(token_url, json=payload)
    if not response.ok:
        raise RuntimeError(f"SugarCRM auth failed ({response.status_code}): {response.text}")
    
    return response.json()["access_token"]

def _get_contacts_page(token: str, offset: int, limit: int) -> dict[str, Any]:
    """Fetches a single page of contacts."""
    base_url = os.environ.get("SUGARCRM_API_BASE", "").rstrip("/")
    url = f"{base_url}/Contacts"
    headers = {"OAuth-Token": token}
    params = {"offset": offset, "max_num": limit}
    
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        raise RuntimeError(f"SugarCRM API call failed ({response.status_code}): {response.text}")
    
    return response.json()

def fetch_contacts() -> Generator[dict[str, Any], None, None]:
    """
    Yields IncomingContact dicts from SugarCRM.
    """
    token = _authenticate()
    offset = 0
    limit = 100

    while True:
        data = _get_contacts_page(token, offset, limit)
        records = data.get("records", [])
        
        if not records:
            break

        for record in records:
            yield sugarcrm_contact_to_incoming(record)

        next_offset = data.get("next_offset", -1)
        if next_offset == -1 or next_offset <= offset:
            break
        offset = next_offset