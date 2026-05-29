import os
import requests
from typing import Any, Iterable
from src.integrations.zendesk_sell.mapping import zendesk_sell_contact_to_incoming

def _get_contacts_page(base_url: str, token: str, page: int) -> dict[str, Any]:
    """
    Indirection point for HTTP GET to Zendesk Sell /contacts.
    """
    url = f"{base_url.rstrip('/')}/contacts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    params = {
        "page": page,
        "per_page": 100
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"Zendesk Sell API error: {response.status_code} - {response.text} "
            f"at URL: {url}"
        )
    
    return response.json()

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Fetches person-type contacts from Zendesk Sell and yields IncomingContact dicts.
    """
    token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Missing required environment variable: ZENDESK_SELL_ACCESS_TOKEN")
    
    base_url = os.environ.get("ZENDESK_SELL_API_BASE", "https://api.getbase.com/v2")
    
    page = 1
    while True:
        data = _get_contacts_page(base_url, token, page)
        items = data.get("items", [])
        
        if not items:
            break
            
        for envelope in items:
            contact_data = envelope.get("data", {})
            
            # Per definition, we only pull person-type contacts. 
            # In Sell, organizations have is_organization=True.
            if contact_data.get("is_organization") is True:
                continue
                
            yield zendesk_sell_contact_to_incoming(contact_data)
            
        page += 1