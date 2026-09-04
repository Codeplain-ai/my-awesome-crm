import logging
import os
from typing import Any, Callable, List, Dict
import httpx

from .mapping import map_contact

logger = logging.getLogger(__name__)

# Metadata for the host ingest service
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Primary entry point for the SugarCRM integration.
    Orchestrates authentication and paginated fetching of Contacts.
    """
    # Required variables
    endpoint = os.environ.get("SUGARCRM_ENDPOINT")
    username = os.environ.get("SUGARCRM_USERNAME")
    password = os.environ.get("SUGARCRM_PASSWORD")
    client_id = os.environ.get("SUGARCRM_CLIENT_ID")
    
    # Optional variable (can be empty string)
    client_secret = os.environ.get("SUGARCRM_CLIENT_SECRET", "")

    missing = []
    if not endpoint: missing.append("SUGARCRM_ENDPOINT")
    if not username: missing.append("SUGARCRM_USERNAME")
    if not password: missing.append("SUGARCRM_PASSWORD")
    if not client_id: missing.append("SUGARCRM_CLIENT_ID")

    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)

    base_url = f"{endpoint.rstrip('/')}/rest/v11"
    
    all_records = []
    
    try:
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            # 1. Authenticate
            token = _acquire_token(client, client_id, client_secret, username, password)
            headers = {"OAuth-Token": token}

            # 2. Fetch Contacts with Pagination
            offset = 0
            
            while offset != -1:
                params = {
                    "fields": "id,first_name,last_name,name,full_name,email,email1,title,account_name,date_entered,date_modified",
                    "max_num": 200,
                    "offset": offset,
                    "order_by": "date_entered:asc"
                }
                
                response = client.get("/Contacts", params=params, headers=headers)
                if response.status_code != 200:
                    logger.error(f"SugarCRM API error: {response.status_code} {response.text}")
                    response.raise_for_status()
                
                data = response.json()
                records = data.get("records", [])
                
                for raw_rec in records:
                    try:
                        mapped_data = map_contact(raw_rec)
                        all_records.append({
                            "data_type": "contact",
                            "data": mapped_data
                        })
                    except ValueError as e:
                        # Skip-and-log policy for per-record mapping concerns
                        rec_id = raw_rec.get("id", "unknown")
                        logger.warning(f"Skipping SugarCRM record {rec_id}: {str(e)}")
                    except Exception as e:
                        # Defensive: unexpected mapping errors are also skipped
                        rec_id = raw_rec.get("id", "unknown")
                        logger.error(f"Unexpected error mapping SugarCRM record {rec_id}: {str(e)}", exc_info=True)

                offset = data.get("next_offset", -1)
    except httpx.HTTPError as e:
        logger.error(f"Transport error communicating with SugarCRM: {str(e)}")
        raise

    return all_records

def _acquire_token(client: httpx.Client, client_id: str, client_secret: str, username: str, password: str) -> str:
    """Retrieves an access token using the password grant flow."""
    payload = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "platform": "base"
    }
    
    response = client.post("/oauth2/token", json=payload)
    if response.status_code != 200:
        error_info = response.text
        try:
            error_data = response.json()
            error_info = f"{error_data.get('error')}: {error_data.get('error_message')}"
        except Exception:
            pass
        logger.error(f"SugarCRM Authentication failed: {error_info}")
        response.raise_for_status()
        
    return response.json()["access_token"]