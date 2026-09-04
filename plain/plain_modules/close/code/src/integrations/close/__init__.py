import logging
import os
from typing import Any, Callable, List

from .client import CloseClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# Module-level DATA_TYPE for records produced by this integration
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Fetch contacts from Close CRM and map them to the host's Record format.
    Exposes the required plug-in interface for the ingest service.
    """
    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        logger.error("Required environment variable CLOSE_API_KEY is missing")
        raise RuntimeError("CLOSE_API_KEY")

    client = CloseClient(api_key)
    produced_records = []
    
    try:
        for contact_batch in client.list_contacts():
            for raw_contact in contact_batch:
                try:
                    mapped_data = map_contact(raw_contact)
                    produced_records.append({
                        "data_type": DATA_TYPE,
                        "data": mapped_data
                    })
                except ValueError as e:
                    # Per-record skip-and-log policy for mapping errors
                    contact_id = raw_contact.get("id", "unknown")
                    logger.warning(
                        f"Skipping Close contact {contact_id} due to mapping error: {str(e)}"
                    )
                except Exception as e:
                    # Unexpected errors in mapping logic are logged, but processing continues
                    contact_id = raw_contact.get("id", "unknown")
                    logger.error(
                        f"Unexpected error mapping Close contact {contact_id}: {str(e)}",
                        exc_info=True
                    )
                    continue
                    
    except Exception as e:
        # Re-raise to ensure host commits no partial writes on fetch failure
        logger.error(f"Integration 'close' failed: {str(e)}")
        raise

    return produced_records