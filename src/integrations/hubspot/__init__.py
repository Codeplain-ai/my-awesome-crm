import logging
import os
from typing import Any, Callable

from .client import HubSpotClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# The source identifier for this integration
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """
    Fetch contacts from HubSpot and map them to the host's conventional contact shape.
    """
    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Required environment variable 'HUBSPOT_ACCESS_TOKEN' is missing or empty")

    client = HubSpotClient(access_token)
    produced = []

    try:
        for hubspot_record in client.list_contacts():
            external_id = hubspot_record.get("id")
            try:
                mapped_data = map_contact(hubspot_record)
                produced.append({
                    "data_type": "contact",
                    "data": mapped_data
                })
            except ValueError as e:
                logger.warning(
                    f"Skipping HubSpot contact {external_id}: {str(e)}",
                    extra={"external_id": external_id, "error": str(e)}
                )
            except Exception as e:
                # Only ValueError is caught by the skip-and-log policy.
                # Other exceptions (like mapping bugs) crash the batch.
                raise

    except Exception as e:
        logger.error(f"HubSpot fetch failed: {str(e)}")
        raise

    return produced
