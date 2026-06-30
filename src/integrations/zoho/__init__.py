import os
from typing import Any, Callable, List, Dict
from .client import ZohoClient
from .mapping import map_contact

DATA_TYPE = "contact"

__all__ = ["fetch", "DATA_TYPE"]

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Entry point for the Zoho integration.
    Pulls Contacts from Zoho CRM and maps them to host-standard records.
    """
    credentials = {}
    required_vars = [
        "ZOHO_ACCOUNTS_HOST",
        "ZOHO_API_HOST",
        "ZOHO_CLIENT_ID",
        "ZOHO_CLIENT_SECRET",
        "ZOHO_REFRESH_TOKEN",
    ]
    
    for var in required_vars:
        val = os.environ.get(var)
        if not val:
            raise RuntimeError(var)
        credentials[var] = val

    client = ZohoClient(
        accounts_host=credentials["ZOHO_ACCOUNTS_HOST"],
        api_host=credentials["ZOHO_API_HOST"],
        client_id=credentials["ZOHO_CLIENT_ID"],
        client_secret=credentials["ZOHO_CLIENT_SECRET"],
        refresh_token=credentials["ZOHO_REFRESH_TOKEN"],
    )

    raw_contacts = client.fetch_all_contacts()
    
    results = []
    for raw in raw_contacts:
        mapped_data = map_contact(raw)
        results.append({
            "data_type": "contact",
            "data": mapped_data
        })
        
    return results