from typing import Any, Callable, List
import logging
import os
from .client import DynamicsClient
from .mapping import map_contact_record

logger = logging.getLogger(__name__)

# The data_type this integration primarily produces.
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Integration entry point for Dynamics 365.
    Fetches contacts from Dataverse Web API and maps them to the host's Contact shape.
    """
    client_id = os.environ.get("DYNAMICS_CLIENT_ID")
    client_secret = os.environ.get("DYNAMICS_CLIENT_SECRET")
    tenant_id = os.environ.get("DYNAMICS_TENANT_ID")
    endpoint = os.environ.get("DYNAMICS_ENDPOINT")

    # Requirement: Raise RuntimeError naming any environment variable key that is missing or empty.
    missing = [k for k, v in {
        "DYNAMICS_CLIENT_ID": client_id,
        "DYNAMICS_CLIENT_SECRET": client_secret,
        "DYNAMICS_TENANT_ID": tenant_id,
        "DYNAMICS_ENDPOINT": endpoint
    }.items() if not v]
    
    if missing:
        raise RuntimeError(f"Missing required environment variables for Dynamics: {', '.join(missing)}")

    # Normalizing endpoint for consistent URL construction
    endpoint = endpoint.rstrip("/")
    if not endpoint.startswith("https://"):
        raise RuntimeError(f"DYNAMICS_ENDPOINT must be an https URL, got: {endpoint}")

    client = DynamicsClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        endpoint=endpoint
    )

    all_mapped_records: List[dict[str, Any]] = []
    
    try:
        # Iterate through pages of contacts
        for page in client.list_contacts():
            for raw_record in page:
                try:
                    mapped_data = map_contact_record(raw_record)
                    all_mapped_records.append({
                        "data_type": "contact",
                        "data": mapped_data
                    })
                except ValueError as e:
                    # Requirement: skip-and-log batch policy for ValueError
                    ext_id = raw_record.get("contactid", "unknown")
                    logger.warning(
                        f"Skipping Dynamics record {ext_id} due to mapping error: {str(e)}",
                        extra={"external_id": ext_id, "error": str(e)}
                    )
                except Exception as e:
                    # Requirement: Processing continues with remaining records; errors log and skip.
                    ext_id = raw_record.get("contactid", "unknown")
                    logger.error(
                        f"Unexpected error mapping Dynamics record {ext_id}: {str(e)}",
                        exc_info=True
                    )
    except Exception as e:
        # Requirement: Errors that are not per-record mapping concerns are raised by the fetch entry point.
        logger.error(f"Dynamics fetch failed: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to fetch data from Dynamics: {str(e)}")

    return all_mapped_records