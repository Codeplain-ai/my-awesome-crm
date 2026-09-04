import logging
import os
from typing import Any, Callable, List

from .client import SalesforceClient
from .mapping import map_contact_record

logger = logging.getLogger(__name__)

# Provider identifier
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Entry point for the Salesforce integration.
    Fetches contacts from Salesforce REST API and maps them to the host format.
    """
    # 1. Credentials from environment
    endpoint = os.environ.get("SALESFORCE_ENDPOINT")
    client_id = os.environ.get("SALESFORCE_CLIENT_ID")
    client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")

    if not all([endpoint, client_id, client_secret]):
        missing = [k for k, v in {
            "SALESFORCE_ENDPOINT": endpoint,
            "SALESFORCE_CLIENT_ID": client_id,
            "SALESFORCE_CLIENT_SECRET": client_secret
        }.items() if not v]
        raise RuntimeError(f"Missing required Salesforce credentials: {', '.join(missing)}")

    # 2. Initialize client and fetch
    client = SalesforceClient(endpoint, client_id, client_secret)
    
    # get_stored is provided by the host but not strictly required for 
    # simple upsert logic unless we wanted to do delta-detection here.
    # The host ingest.py handles the actual upsert comparison.
    
    all_mapped_records = []
    
    try:
        for record in client.get_all_contacts():
            external_id = record.get("Id", "unknown")
            try:
                mapped_data = map_contact_record(record)
                all_mapped_records.append({
                    "data_type": "contact",
                    "data": mapped_data
                })
            except ValueError as ve:
                # Per-record skip-and-log policy
                logger.warning(
                    f"Skipping Salesforce contact {external_id} due to mapping error: {ve}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error mapping Salesforce contact {external_id}: {e}",
                    exc_info=True
                )
                # We continue with other records as per policy
    except Exception as e:
        logger.error(f"Salesforce fetch failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to fetch data from Salesforce: {e}")

    return all_mapped_records