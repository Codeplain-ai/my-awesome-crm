import logging
from typing import Any, Callable, Dict, List

from .client import SugarCrmClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# The host uses these to discover and configure the integration.
__all__ = ["fetch", "DATA_TYPE"]

# Module-level data type for host fallback
DATA_TYPE = "contact"


def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Entry point for :SugarCrmIntegration:.
    """
    logger.info("Starting SugarCRM contact ingest")

    try:
        client = SugarCrmClient()
    except RuntimeError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise

    token = client._get_token()

    all_contacts: List[Dict[str, Any]] = []
    offset = 0
    
    while offset != -1:
        records, next_offset = client.fetch_contacts_page(token, offset)
        logger.info(f"Fetched {len(records)} contacts from SugarCRM (offset: {offset})")
        all_contacts.extend(records)
        offset = next_offset

    results = []
    for raw in all_contacts:
        mapped_data = map_contact(raw)
        results.append({
            "data_type": "contact",
            "data": mapped_data
        })

    logger.info(f"SugarCRM ingest complete. Produced {len(results)} records.")
    return results