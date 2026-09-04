import logging
from typing import Any, Callable, List, Dict

from .client import NimbleClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# Default data type for this integration
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Fetch contacts from Nimble and map them to the internal format.
    
    Args:
        get_stored: Callback to retrieve existing records from the host store.
                   The host passes this in per the integration contract.
    """
    client = NimbleClient()
    produced_records = []
    
    logger.info("Starting Nimble integration fetch")
    
    try:
        # The client handles pagination internally via a generator.
        # list_person_contacts() raises RuntimeError if credentials/auth fails.
        for nimble_record in client.list_person_contacts():
            external_id = nimble_record.get("id", "unknown")
            try:
                mapped_data = map_contact(nimble_record)
                produced_records.append({
                    "data_type": DATA_TYPE,
                    "data": mapped_data
                })
            except ValueError as ve:
                # Requirement: skip-and-log batch policy for per-record mapping errors.
                logger.warning(
                    f"Skipping Nimble record {external_id}: {str(ve)}",
                    extra={"external_id": external_id, "error": str(ve)}
                )
            except Exception as e:
                # Catch unexpected per-record mapping errors to avoid crashing the whole batch.
                logger.error(
                    f"Unexpected error mapping Nimble record {external_id}",
                    exc_info=True,
                    extra={"external_id": external_id}
                )
                
    except Exception as e:
        # Transport, Auth, or API errors propagate to fail the whole batch.
        # No partial writes occur as the host only commits if fetch returns successfully.
        logger.error(f"Nimble integration failed: {str(e)}", exc_info=True)
        raise RuntimeError(f"Nimble integration failed: {str(e)}")

    logger.info(f"Nimble fetch complete. Produced {len(produced_records)} records.")
    return produced_records