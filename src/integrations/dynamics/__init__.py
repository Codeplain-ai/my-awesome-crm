import logging
from typing import Any, Callable, List, Dict
from .client import DynamicsClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# The source identifier for this integration
PROVIDER_ID = "dynamics"
# Default data type for records emitted by this integration
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Entry point for the Dynamics 365 integration.

    Orchestrates authentication, querying, and mapping of contact records.
    Implements skip-and-log batch policy for mapping errors.
    """
    client = DynamicsClient()
    all_records = []

    try:
        # Dynamics pagination: generator yielding pages of records
        for page in client.get_contacts():
            for raw_record in page:
                external_id = raw_record.get("contactid")
                try:
                    mapped_data = map_contact(raw_record)
                    all_records.append({
                        "data_type": DATA_TYPE,
                        "data": mapped_data
                    })
                except ValueError as e:
                    logger.warning(
                        f"Skipping Dynamics contact {external_id}: {str(e)}",
                        extra={"external_id": external_id, "provider": PROVIDER_ID}
                    )
                except Exception as e:
                    # Unhandled exceptions in mapping stop the whole batch
                    logger.error(f"Unexpected error mapping Dynamics record {external_id}: {str(e)}")
                    raise
    except Exception as e:
        logger.error(f"Dynamics integration failed: {str(e)}")
        raise

    return all_records
