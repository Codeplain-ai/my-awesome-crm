import os as _os
import logging as _logging
from typing import List as _List, Dict as _Dict, Any as _Any, Optional as _Optional
import httpx as _httpx

from .mapping import map_contact_record as _map_contact_record

__all__ = ["fetch_contacts"]

_logger = _logging.getLogger(__name__)

def _get_credentials() -> _Dict[str, str]:
    """Reads credentials from environment variables."""
    keys = ["SALESFORCE_ENDPOINT", "SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"]
    creds = {}
    for key in keys:
        val = _os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing required environment variable: {key}")
        creds[key] = val
    return creds

def _acquire_token(creds: _Dict[str, str]) -> tuple[str, str]:
    """Acquires OAuth token and instance URL."""
    url = f"{creds['SALESFORCE_ENDPOINT'].rstrip('/')}/services/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": creds["SALESFORCE_CLIENT_ID"],
        "client_secret": creds["SALESFORCE_CLIENT_SECRET"],
    }
    
    response = _httpx.post(url, data=data)
    if response.status_code != 200:
        _logger.error(f"Salesforce auth failed: {response.text}")
        raise RuntimeError(f"Salesforce authentication failed with status {response.status_code}")
    
    payload = response.json()
    return payload["access_token"], payload["instance_url"]

def fetch_contacts() -> _List[_Dict[str, _Any]]:
    """
    Main entry point for the Salesforce integration.
    Fetches, paginates, and maps Salesforce contacts.
    """
    creds = _get_credentials()
    token, instance_url = _acquire_token(creds)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    # Pinned SOQL query
    query = "SELECT Id, Name, FirstName, LastName, Email, Phone, MobilePhone, Title, Account.Name FROM Contact"
    next_url: _Optional[str] = f"/services/data/v60.0/query/?q={query}"
    
    all_incoming: _List[_Dict[str, _Any]] = []
    
    while next_url:
        full_url = f"{instance_url.rstrip('/')}{next_url}"
        response = _httpx.get(full_url, headers=headers)
        
        if response.status_code != 200:
            _logger.error(f"Salesforce query failed: {response.text}")
            raise RuntimeError(f"Salesforce API returned error {response.status_code}")
            
        page_data = response.json()
        records = page_data.get("records", [])
        
        for record in records:
            try:
                mapped = _map_contact_record(record)
                all_incoming.append(mapped)
            except ValueError as e:
                # Skip-and-log batch failure policy
                record_id = record.get("Id", "UNKNOWN")
                _logger.warning(f"Skipping malformed Salesforce record {record_id}: {str(e)}")
        
        # Pagination: nextRecordsUrl is provided if 'done' is false
        if not page_data.get("done", True):
            next_url = page_data.get("nextRecordsUrl")
        else:
            next_url = None
            
    return all_incoming