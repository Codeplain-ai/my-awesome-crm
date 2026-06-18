import logging
import httpx
from typing import Iterable, Any
from .config import get_credentials
from .mapping import map_copper_contact

__all__ = ["fetch_contacts"]

logger = logging.getLogger(__name__)

PAGE_SIZE = 200
BASE_URL = "https://api.copper.com/developer_api/v1/people/search"

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Implementation of :CopperIntegration: fetch.
    Walks pagination and yields mapped :IncomingContact: records.
    """
    headers = get_credentials()
    contacts = []
    page_number = 1

    with httpx.Client(headers=headers, timeout=30.0) as client:
        while True:
            logger.info(f"Fetching Copper people page {page_number}")
            
            payload = {
                "page_number": page_number,
                "page_size": PAGE_SIZE
            }
            
            response = client.post(BASE_URL, json=payload)
            
            # Propagate transport/auth/server errors per requirements
            response.raise_for_status()
            
            records = response.json()
            if not isinstance(records, list):
                logger.error(f"Unexpected response format from Copper: {type(records)}")
                break

            for record in records:
                try:
                    mapped = map_copper_contact(record)
                    contacts.append(mapped)
                except ValueError as ve:
                    # Skip-and-log policy for malformed records
                    record_id = record.get("id", "unknown")
                    logger.warning(
                        f"Skipping malformed Copper record {record_id}: {str(ve)}",
                        extra={"provider_id": "copper", "external_id": record_id, "error": str(ve)}
                    )
                except Exception:
                    # Non-mapping errors should propagate
                    raise

            # Pagination check: stop if we got fewer records than requested
            if len(records) < PAGE_SIZE:
                break
            
            page_number += 1

    return contacts