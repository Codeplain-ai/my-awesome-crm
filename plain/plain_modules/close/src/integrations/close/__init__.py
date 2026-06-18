import logging
from typing import List, Dict, Any
from .client import CloseClient
from .mapping import map_close_contact

logger = logging.getLogger(__name__)

__all__ = ["fetch_contacts"]

def fetch_contacts() -> List[Dict[str, Any]]:
    """
    Integration entry point. Fetches and maps Close contacts.
    Applies skip-and-log policy for mapping errors.
    """
    client = CloseClient()
    incoming_contacts = []

    for raw_record in client.list_contacts():
        try:
            mapped = map_close_contact(raw_record)
            incoming_contacts.append(mapped)
        except ValueError as e:
            # Skip-and-log policy: name the record's id in the log
            rec_id = raw_record.get("id", "unknown")
            logger.warning(
                f"Skipping malformed Close record {rec_id}: {str(e)}"
            )
        except Exception as e:
            # Non-mapping errors (auth, network) propagate
            raise e

    return incoming_contacts