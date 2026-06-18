import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from .mapper import map_zendesk_contact

__all__ = ["fetch_contacts"]

logger = logging.getLogger(__name__)

BASE_URL = "https://api.getbase.com/v2/contacts"

def _get_token() -> str:
    token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Missing environment variable: ZENDESK_SELL_ACCESS_TOKEN")
    return token

def fetch_contacts() -> List[Dict[str, Any]]:
    """
    Entry point for the host's ingest service.
    Pulls contacts from Zendesk Sell v2 API and maps them to IncomingContact format.
    """
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "CRM-Ingest-Service/1.0 (Integration: zendesk_sell)"
    }
    
    results: List[Dict[str, Any]] = []
    next_page_url: Optional[str] = f"{BASE_URL}?per_page=100"

    with httpx.Client(headers=headers) as client:
        while next_page_url:
            logger.info(f"Fetching Zendesk Sell contacts from: {next_page_url}")
            response = client.get(next_page_url)
            
            # Raise for 4xx/5xx to allow the host ingest logic to handle/retry 
            # and rollback as per [resource]ingest.py
            response.raise_for_status()
            
            payload = response.json()
            items = payload.get("items", [])
            
            for item in items:
                data = item.get("data", {})
                try:
                    mapped = map_zendesk_contact(data)
                    results.append(mapped)
                except ValueError as ve:
                    # Skip-and-log policy for malformed records
                    record_id = data.get("id", "unknown")
                    logger.warning(
                        f"Skipping malformed Zendesk Sell record {record_id}: {str(ve)}"
                    )

            # Pagination: Follow meta.links.next_page
            next_page_url = payload.get("meta", {}).get("links", {}).get("next_page")

    return results