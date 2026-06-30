import os
import logging
from typing import Any, Callable, Dict, List, Optional
import httpx

from .mapping import map_pipedrive_person_to_contact

logger = logging.getLogger(__name__)

# Module-level constant for the host ingest process
DATA_TYPE = "contact"

__all__ = ["DATA_TYPE", "fetch"]


def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Entry point for the Pipedrive integration.
    Fetches all Person records from Pipedrive and maps them to Contact records.
    """
    api_token = os.environ.get("PIPEDRIVE_API_TOKEN")
    company_domain = os.environ.get("PIPEDRIVE_COMPANY_DOMAIN")

    if not api_token:
        raise RuntimeError("PIPEDRIVE_API_TOKEN")
    if not company_domain:
        raise RuntimeError("PIPEDRIVE_COMPANY_DOMAIN")

    base_url = f"https://{company_domain}.pipedrive.com/v1/persons"
    
    all_mapped_records = []
    start = 0
    limit = 100
    has_more = True

    # Use a timeout to prevent hanging the ingest service
    timeout = httpx.Timeout(10.0, connect=5.0)

    with httpx.Client(timeout=timeout) as client:
        while has_more:
            params = {
                "api_token": api_token,
                "start": start,
                "limit": limit
            }
            
            try:
                response = client.get(base_url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as e:
                msg = f"Pipedrive API HTTP error: {e.response.status_code} - {e.response.text}"
                logger.error(msg, extra={"url": base_url, "start": start})
                raise RuntimeError(msg)
            except httpx.RequestError as e:
                msg = f"Pipedrive API request failed: {str(e)}"
                logger.error(msg)
                raise RuntimeError(msg)

            if not isinstance(payload, dict) or not payload.get("success"):
                error_info = payload.get("error") if isinstance(payload, dict) else "Non-dict response"
                msg = f"Pipedrive API error: {error_info or 'Unknown error'}"
                logger.error(msg, extra={"payload": payload})
                raise RuntimeError(msg)

            data_list = payload.get("data") or []
            for person in data_list:
                mapped_data = map_pipedrive_person_to_contact(person)
                all_mapped_records.append({
                    "data_type": DATA_TYPE,
                    "data": mapped_data
                })

            # Pagination handling
            pagination = payload.get("additional_data", {}).get("pagination", {})
            has_more = pagination.get("more_items_in_collection", False)
            start = pagination.get("next_start")

            if has_more and start is None:
                logger.warning("Pipedrive indicated more items but next_start is missing. Terminating pagination.")
                break

    logger.info(f"Successfully fetched and mapped {len(all_mapped_records)} contacts from Pipedrive.")
    return all_mapped_records