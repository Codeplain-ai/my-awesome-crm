import os
import logging
import httpx
from typing import Any, List, Dict, Optional
from .mapping import map_contact

logger = logging.getLogger(__name__)

def _get_credentials() -> Dict[str, str]:
    keys = [
        "SUGARCRM_ENDPOINT",
        "SUGARCRM_CLIENT_ID",
        "SUGARCRM_CLIENT_SECRET",
        "SUGARCRM_USERNAME",
        "SUGARCRM_PASSWORD",
    ]
    creds = {}
    for key in keys:
        val = os.environ.get(key)
        if val is None or (val == "" and key != "SUGARCRM_CLIENT_SECRET"):
            raise RuntimeError(f"Missing required environment variable: {key}")
        creds[key] = val
    return creds

def _get_token(client: httpx.Client, creds: Dict[str, str]) -> str:
    url = f"{creds['SUGARCRM_ENDPOINT'].rstrip('/')}/rest/v11/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": creds["SUGARCRM_CLIENT_ID"],
        "client_secret": creds["SUGARCRM_CLIENT_SECRET"],
        "username": creds["SUGARCRM_USERNAME"],
        "password": creds["SUGARCRM_PASSWORD"],
        "platform": "base"
    }
    
    response = client.post(url, json=payload)
    if response.status_code != 200:
        logger.error(
            "SugarCRM token acquisition failed",
            extra={"status_code": response.status_code, "body": response.text}
        )
        response.raise_for_status()
        
    data = response.json()
    return data["access_token"]

def _fetch_page(
    client: httpx.Client, 
    endpoint: str, 
    token: str, 
    offset: int = 0
) -> Dict[str, Any]:
    url = f"{endpoint.rstrip('/')}/rest/v11/Contacts"
    params = {
        "fields": "id,first_name,last_name,name,full_name,email,email1,phone_work,phone_mobile,title,account_name",
        "max_num": 200,
        "order_by": "date_entered:asc",
    }
    if offset > 0:
        params["offset"] = offset

    headers = {"OAuth-Token": token}
    
    response = client.get(url, params=params, headers=headers)
    if response.status_code != 200:
        logger.error(
            "SugarCRM fetch page failed",
            extra={"status_code": response.status_code, "body": response.text, "offset": offset}
        )
        response.raise_for_status()
        
    return response.json()

def fetch_contacts() -> List[Dict[str, Any]]:
    """
    Orchestrates ingestion from SugarCRM.
    Returns a list of IncomingContact dicts.
    """
    creds = _get_credentials()
    results: List[Dict[str, Any]] = []
    
    # Use a single client for connection pooling
    with httpx.Client(timeout=30.0) as client:
        token = _get_token(client, creds)
        
        offset = 0
        while offset != -1:
            page_data = _fetch_page(client, creds["SUGARCRM_ENDPOINT"], token, offset)
            records = page_data.get("records", [])
            
            for raw_record in records:
                try:
                    mapped = map_contact(raw_record)
                    results.append(mapped)
                except ValueError as e:
                    record_id = raw_record.get("id", "unknown")
                    logger.warning(
                        f"Skipping SugarCRM record '{record_id}' due to mapping error: {str(e)}"
                    )
            
            offset = page_data.get("next_offset", -1)
            
    return results