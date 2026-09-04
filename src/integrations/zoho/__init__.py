import logging
from typing import Any, Callable, List, Dict
from .client import ZohoClient
from .mapping import map_zoho_contact

logger = logging.getLogger(__name__)

# The identifier for this provider
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Primary entry point for the Zoho CRM integration.
    Fetches contacts from Zoho, maps them to the internal format, and returns them.
    
    :param get_stored: A callback provided by the host to retrieve existing records.
    :return: A list of dicts with 'data_type' and 'data' keys.
    """
    client = ZohoClient()
    
    try:
        # 1. Get Access Token
        client.authenticate()
        
        # 2. Fetch all pages of contacts
        raw_contacts = client.list_contacts()
        
        # 3. Map records with skip-and-log batch policy
        produced_records = []
        for raw_record in raw_contacts:
            # IDENTITY_FIELD 'external_id' is mapped from 'id'
            external_id = raw_record.get("id", "unknown")
            try:
                mapped_data = map_zoho_contact(raw_record)
                produced_records.append({
                    "data_type": DATA_TYPE,
                    "data": mapped_data
                })
            except ValueError as e:
                # Per-record skip-and-log policy
                logger.warning(
                    f"Skipping Zoho record {external_id} due to mapping error: {str(e)}",
                    extra={"external_id": external_id, "error": str(e)}
                )
            except Exception as e:
                # Defensive programming: unexpected errors in mapping also logged and skipped
                logger.error(
                    f"Unexpected error mapping Zoho record {external_id}: {str(e)}",
                    exc_info=True
                )
        
        return produced_records

    except Exception as e:
        # Errors acquiring data (auth, transport) propagate as RuntimeError
        logger.error(f"Zoho integration fetch failed: {str(e)}", exc_info=True)
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Zoho integration failed: {str(e)}") from e