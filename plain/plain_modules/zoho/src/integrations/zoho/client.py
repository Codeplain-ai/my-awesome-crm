import os
import requests
from typing import Any, Dict, Iterable, Optional
from src.integrations.zoho.mapping import zoho_contact_to_incoming

def _get_credentials() -> Dict[str, str]:
    """Reads Zoho credentials from the environment."""
    client_id = os.environ.get("ZOHO_CLIENT_ID", "")
    client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
    refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN", "")
    
    if not client_id:
        raise RuntimeError("Missing required Zoho credential: ZOHO_CLIENT_ID")
    if not client_secret:
        raise RuntimeError("Missing required Zoho credential: ZOHO_CLIENT_SECRET")
    if not refresh_token:
        raise RuntimeError("Missing required Zoho credential: ZOHO_REFRESH_TOKEN")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "accounts_domain": os.environ.get("ZOHO_ACCOUNTS_DOMAIN", "accounts.zoho.com"),
        "api_domain": os.environ.get("ZOHO_API_DOMAIN", "www.zohoapis.com"),
    }

def _refresh_access_token(client_id: str, client_secret: str, refresh_token: str, accounts_domain: str) -> str:
    """Exchanges refresh token for a short-lived access token."""
    url = f"https://{accounts_domain}/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    
    response = requests.post(url, params=params)
    if not response.ok:
        raise RuntimeError(f"Failed to refresh Zoho token. Status: {response.status_code}, URL: {url}, Body: {response.text}")
    
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise RuntimeError(f"Zoho token response missing access_token: {data}")
        
    return access_token

def _get_contacts_page(api_domain: str, access_token: str, page: int) -> Dict[str, Any]:
    """Fetches a single page of contacts from Zoho CRM."""
    url = f"https://{api_domain}/crm/v2/Contacts"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    params = {"page": page, "per_page": 200}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 204:
        return {"data": [], "info": {"more_records": False}}
        
    if not response.ok:
        raise RuntimeError(f"Zoho API error. Status: {response.status_code}, URL: {url}, Body: {response.text}")
        
    return response.json()

def fetch_contacts() -> list[Dict[str, Any]]:
    """
    Main entry point for the Zoho integration.
    Discovered by the host system.
    """
    creds = _get_credentials()
    access_token = _refresh_access_token(
        creds["client_id"], 
        creds["client_secret"], 
        creds["refresh_token"], 
        creds["accounts_domain"]
    )
    
    all_contacts = []
    page = 1
    has_more = True
    
    while has_more:
        result = _get_contacts_page(creds["api_domain"], access_token, page)
        records = result.get("data")
        
        if not records:
            break
            
        for record in records:
            all_contacts.append(zoho_contact_to_incoming(record))
            
        info = result.get("info", {})
        has_more = info.get("more_records", False)
        page += 1
        
    return all_contacts