import logging
import os
from typing import Any, Dict, Iterable
import httpx

from .mapper import map_pipedrive_person

__all__ = ["fetch_contacts"]

logger = logging.getLogger(__name__)

def fetch_contacts() -> Iterable[Dict[str, Any]]:
    """
    Pipedrive integration entry point. Fetches all persons from Pipedrive API
    and returns mapped IncomingContact dicts.
    """
    api_token = os.environ.get("PIPEDRIVE_API_TOKEN")
    if not api_token:
        raise RuntimeError("PIPEDRIVE_API_TOKEN")
    
    company_domain = os.environ.get("PIPEDRIVE_COMPANY_DOMAIN")
    if not company_domain:
        raise RuntimeError("PIPEDRIVE_COMPANY_DOMAIN")

    base_url = f"https://{company_domain}.pipedrive.com/v1/persons"
    
    contacts = []
    start = 0
    limit = 100
    more_items = True

    with httpx.Client(timeout=30.0) as client:
        while more_items:
            params = {
                "api_token": api_token,
                "start": start,
                "limit": limit
            }
            
            response = client.get(base_url, params=params)
            
            if response.status_code == 401:
                raise RuntimeError(f"Pipedrive auth failed (401): {response.text}")
            response.raise_for_status()
            
            payload = response.json()
            if not payload.get("success"):
                error_msg = payload.get("error", "Unknown Pipedrive API error")
                raise RuntimeError(f"Pipedrive API error: {error_msg}")

            data = payload.get("data") or []
            for record in data:
                try:
                    mapped = map_pipedrive_person(record)
                    contacts.append(mapped)
                except ValueError as e:
                    # Skip-and-log policy
                    record_id = record.get("id", "unknown")
                    logger.warning(
                        f"Skipping Pipedrive record {record_id} due to mapping error: {str(e)}"
                    )

            # Pagination handling
            pagination = payload.get("additional_data", {}).get("pagination", {})
            more_items = pagination.get("more_items_in_collection", False)
            if more_items:
                start = pagination.get("next_start")
                if start is None:
                    break
            else:
                break

    return contacts