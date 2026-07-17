import logging
from typing import Any, Callable, List

from .client import SalesforceClient
from .mapping import map_contact

# Provider identifier as required by :Provider: definition
DATA_TYPE = "contact"
SOURCE = "salesforce"

logger = logging.getLogger(__name__)

def fetch_contacts(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Fetches contacts from Salesforce and returns them in the host's expected format.
    Exposed specifically for contact ingestion.
    """
    return fetch(get_stored)


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Primary entry point for the Salesforce integration.
    Fetches contacts from Salesforce REST API and maps them to the conventional Contact shape.
    """
    client = SalesforceClient()
    
    # The host logic handles idempotency via upserts based on external_id.
    # We fetch all relevant records from the provider.
    raw_records = client.get_all_contacts()
    
    produced_records = []
    
    for raw_record in raw_records:
        try:
            # Apply mapping logic
            mapped_data = map_contact(raw_record)
            
            # Wrap in the format expected by the host ingest service
            produced_records.append({
                "data_type": DATA_TYPE,
                "data": mapped_data
            })
        except ValueError as e:
            # Skip-and-log batch policy as per :ImplementationReqs:
            external_id = raw_record.get("Id", "unknown")
            logger.warning(
                f"Skipping record {external_id} from {SOURCE} due to mapping error: {str(e)}",
                extra={"provider_id": SOURCE, "external_id": external_id}
            )
        except Exception as e:
            # Unexpected errors in mapping are also caught to preserve batch integrity
            external_id = raw_record.get("Id", "unknown")
            logger.error(
                f"Unexpected error mapping record {external_id} from {SOURCE}: {str(e)}",
                exc_info=True
            )
            
    return produced_records