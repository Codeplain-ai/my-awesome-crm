from typing import Any, Callable, List
import logging
from .client import NimbleClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# The default data type for this integration
DATA_TYPE = "contact"

# Public API for the host discovery service
__all__ = ["fetch", "DATA_TYPE"]


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Fetches person contacts from Nimble and maps them to the host's Contact format.
    """
    # Validation of credentials happens during client init per implementation reqs
    client = NimbleClient()
    results = []
    
    try:
        # We only fetch "person" records as per requirements
        for raw_contact in client.list_all_contacts(record_type="person"):
            mapped_data = map_contact(raw_contact)
            results.append({
                "data_type": DATA_TYPE,
                "data": mapped_data
            })
            
        logger.info(f"Nimble integration successfully fetched {len(results)} contacts.")
    except Exception as e:
        logger.error(f"Nimble integration failed during fetch: {str(e)}", exc_info=True)
        raise
        
    return results