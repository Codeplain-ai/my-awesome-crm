import os
import logging
import httpx
from typing import Dict, Any, List, Optional, Generator

logger = logging.getLogger(__name__)

def get_credentials() -> Dict[str, str]:
    """Reads Zoho credentials from environment variables."""
    keys = [
        "ZOHO_ACCOUNTS_HOST",
        "ZOHO_API_HOST",
        "ZOHO_CLIENT_ID",
        "ZOHO_CLIENT_SECRET",
        "ZOHO_REFRESH_TOKEN"
    ]
    creds = {}
    for key in keys:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing required environment variable: {key}")
        creds[key] = val
    return creds

def get_access_token(creds: Dict[str, str]) -> str:
    """Exchanges refresh token for access token via Zoho OAuth."""
    url = f"{creds['ZOHO_ACCOUNTS_HOST'].rstrip('/')}/oauth/v2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": creds["ZOHO_CLIENT_ID"],
        "client_secret": creds["ZOHO_CLIENT_SECRET"],
        "refresh_token": creds["ZOHO_REFRESH_TOKEN"]
    }
    
    with httpx.Client() as client:
        response = client.post(url, data=data)
        if response.status_code != 200:
            logger.error(f"Failed to refresh Zoho token: {response.text}")
            response.raise_for_status()
        
        return response.json()["access_token"]

def fetch_raw_contacts(creds: Dict[str, str], token: str) -> Generator[Dict[str, Any], None, None]:
    """Iterates through Zoho Contact pages and yields raw record dicts."""
    base_url = f"{creds['ZOHO_API_HOST'].rstrip('/')}/crm/v3/Contacts"
    page = 1
    more_records = True
    
    fields = "id,Full_Name,First_Name,Last_Name,Email,Phone,Mobile,Title,Account_Name"
    
    with httpx.Client() as client:
        while more_records:
            params = {
                "fields": fields,
                "per_page": 200,
                "page": page
            }
            headers = {"Authorization": f"Zoho-oauthtoken {token}"}
            
            response = client.get(base_url, params=params, headers=headers)
            
            if response.status_code == 204:
                return  # No more records
            
            response.raise_for_status()
            payload = response.json()
            
            data = payload.get("data", [])
            for record in data:
                yield record
            
            info = payload.get("info", {})
            more_records = info.get("more_records", False)
            page += 1