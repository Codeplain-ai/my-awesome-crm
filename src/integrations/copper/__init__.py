import os
import logging
from typing import Any, Callable, List

import httpx

from .mapping import map_copper_person_to_contact

logger = logging.getLogger(__name__)

# Integration Metadata
DATA_TYPE = "contact"
BASE_URL = "https://api.copper.com/developer_api/v1"

__all__ = ["DATA_TYPE", "fetch"]


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Copper integration fetch entry point.
    
    Reads credentials from COPPER_API_KEY and COPPER_USER_EMAIL.
    Walks the Copper People search API pages and maps results to host records.
    """
    api_key = os.environ.get("COPPER_API_KEY")
    user_email = os.environ.get("COPPER_USER_EMAIL")

    if not api_key:
        raise RuntimeError("Missing required Copper credential: COPPER_API_KEY")
    if not user_email:
        raise RuntimeError("Missing required Copper credential: COPPER_USER_EMAIL")

    headers = {
        "X-PW-AccessToken": api_key,
        "X-PW-UserEmail": user_email,
        "X-PW-Application": "developer_api",
        "Content-Type": "application/json",
    }

    page_size = 200
    page_number = 1
    all_records = []

    # Use a single client for connection pooling across pages
    with httpx.Client(timeout=60.0) as client:
        while True:
            logger.info(f"Fetching Copper People page {page_number}")
            
            try:
                response = client.post(
                    f"{BASE_URL}/people/search",
                    headers=headers,
                    json={
                        "page_number": page_number,
                        "page_size": page_size,
                    },
                )
            except httpx.RequestError as exc:
                raise RuntimeError(f"Network error while contacting Copper API: {str(exc)}") from exc

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    message = error_data.get("message", response.text)
                except Exception:
                    message = response.text
                
                raise RuntimeError(
                    f"Copper API error (status {response.status_code}): {message}. "
                    f"Request: page_number={page_number}"
                )

            batch = response.json()
            if not isinstance(batch, list):
                raise RuntimeError(
                    f"Unexpected Copper API response format: expected list, got {type(batch).__name__}"
                )

            for person in batch:
                mapped_contact = map_copper_person_to_contact(person)
                all_records.append({
                    "data_type": DATA_TYPE,
                    "data": mapped_contact
                })

            # Pagination check: a page with fewer than page_size records is the final page.
            if len(batch) < page_size:
                logger.info(f"Reached end of Copper People data at page {page_number}")
                break
            
            page_number += 1

    return all_records