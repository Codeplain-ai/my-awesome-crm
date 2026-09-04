import logging
import os
from typing import Any, Callable, Dict, List, Optional

import httpx

from .mapping import map_copper_person_to_contact

logger = logging.getLogger(__name__)

# The Provider identifier
SOURCE = "copper"
# Default data type for this integration
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Fetches people from Copper and maps them to the host's contact format.
    
    Args:
        get_stored: A callback to retrieve existing records (unused by this integration 
                    as it relies on host-side upsert logic).
    """
    api_key = os.environ.get("COPPER_API_KEY")
    user_email = os.environ.get("COPPER_USER_EMAIL")

    missing = []
    if not api_key:
        missing.append("COPPER_API_KEY")
    if not user_email:
        missing.append("COPPER_USER_EMAIL")

    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    base_url = "https://api.copper.com/developer_api/v1"
    headers = {
        "X-PW-AccessToken": api_key,
        "X-PW-UserEmail": user_email,
        "X-PW-Application": "developer_api",
        "Content-Type": "application/json",
    }

    produced_records = []
    page_number = 1
    page_size = 200

    with httpx.Client(base_url=base_url, headers=headers, timeout=30.0) as client:
        while True:
            logger.info(f"Fetching Copper people page {page_number}...")
            
            response = client.post(
                "/people/search",
                json={"page_number": page_number, "page_size": page_size}
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("message", error_detail)
                except Exception:
                    pass
                
                logger.error(f"Copper API error (status {response.status_code}): {error_detail}")
                response.raise_for_status()

            records = response.json()
            if not isinstance(records, list):
                logger.error(f"Unexpected Copper API response format: expected list, got {type(records)}")
                break

            for raw_record in records:
                external_id = raw_record.get("id")
                try:
                    mapped_data = map_copper_person_to_contact(raw_record)
                    produced_records.append({
                        "data_type": DATA_TYPE,
                        "data": mapped_data
                    })
                except ValueError as e:
                    logger.warning(
                        f"Skipping Copper record {external_id}: {str(e)}",
                        extra={"provider_id": SOURCE, "external_id": external_id}
                    )
                except Exception as e:
                    logger.error(
                        f"Unexpected error mapping Copper record {external_id}: {str(e)}",
                        exc_info=True
                    )
                    # We continue per the skip-and-log policy even for unexpected mapping bugs
                    continue

            # Pagination logic: stop when a page returns fewer than page_size records
            if len(records) < page_size:
                break
            
            page_number += 1

    logger.info(f"Copper integration finished. Total records mapped: {len(produced_records)}")
    return produced_records