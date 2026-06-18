import logging
import os
from typing import Iterable, Any
from .client import NimbleClient
from .mapper import map_nimble_contact

logger = logging.getLogger(__name__)

__all__ = ["fetch_contacts"]

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Orchestrates the Nimble integration: fetches person records from the API,
    maps them to IncomingContact format, and applies skip-and-log policy.
    """
    token = os.environ.get("NIMBLE_ACCESS_TOKEN")
    if not token:
        logger.error("NIMBLE_ACCESS_TOKEN environment variable is not set")
        raise RuntimeError("Missing NIMBLE_ACCESS_TOKEN")

    client = NimbleClient(access_token=token)
    
    try:
        for raw_record in client.list_person_contacts():
            try:
                mapped = map_nimble_contact(raw_record)
                yield mapped
            except ValueError as ve:
                # Per contact-mapping.md Error contract and skip-and-log policy
                record_id = raw_record.get("id", "unknown")
                logger.warning(
                    f"Skipping Nimble record {record_id} due to mapping error: {ve}",
                    extra={
                        "provider_id": "nimble",
                        "external_id": record_id,
                        "error": str(ve)
                    }
                )
                continue
    except Exception as e:
        logger.error(
            "Fatal error during Nimble ingestion",
            extra={"error": str(e)},
            exc_info=True
        )
        raise