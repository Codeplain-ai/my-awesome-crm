import logging
import os
from typing import Any, Callable, List, Dict

from .client import ZendeskSellClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# Integration Provider ID
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Zendesk Sell integration entry point.
    Fetches all contacts and maps them to the host shape.
    """
    token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Missing required environment variable: ZENDESK_SELL_ACCESS_TOKEN")

    client = ZendeskSellClient(token=token)
    results: List[Dict[str, Any]] = []

    try:
        for raw_contact in client.list_all_contacts():
            ext_id = raw_contact.get("id")
            try:
                mapped = map_contact(raw_contact)
                results.append({
                    "data_type": "contact",
                    "data": mapped
                })
            except ValueError as ve:
                # Skip-and-log policy: skip individual records that fail mapping
                logger.warning(
                    f"Skipping record {ext_id} due to mapping error: {str(ve)}",
                    extra={"external_id": ext_id, "provider": "zendesk_sell"}
                )
    except Exception as e:
        logger.error(f"Zendesk Sell fetch operation failed: {str(e)}", exc_info=True)
        raise RuntimeError(f"Integration 'zendesk_sell' failed: {str(e)}")

    return results