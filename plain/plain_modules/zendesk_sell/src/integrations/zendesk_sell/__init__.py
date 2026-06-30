from typing import Any, Callable, List, Dict
from .client import ZendeskSellClient
from .mapping import map_contact

__all__ = ["fetch", "DATA_TYPE"]

# The data type this integration primarily produces.
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Integration entry point for Zendesk Sell.
    Fetches all contacts from the Zendesk Sell API and maps them to the host's Contact format.
    """
    client = ZendeskSellClient()
    mapped_records = []

    # The integration lists both persons and organizations (no filter).
    for raw_item in client.list_all_contacts():
        # The business contact lives under the 'data' object of each item.
        raw_contact = raw_item.get("data", {})
        mapped_data = map_contact(raw_contact)
        
        mapped_records.append({
            "data_type": DATA_TYPE,
            "data": mapped_data
        })

    return mapped_records