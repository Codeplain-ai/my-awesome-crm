from typing import Any

from .client import SalesforceClient
from .mapping import map_contact_record

# DATA_TYPE is used by the host if records are returned without a data_type key.
DATA_TYPE = "contact"

__all__ = ["fetch", "DATA_TYPE"]


def fetch(get_stored: Any = None) -> list[dict[str, Any]]:
    """
    Fetches all contact records from Salesforce and maps them.

    This is the entry point for the host's ingest service.
    get_stored is a callback to retrieve existing records, ignored by this integration.
    """
    client = SalesforceClient()
    raw_records = client.query_all_contacts()

    results = []
    for raw in raw_records:
        mapped_data = map_contact_record(raw)
        results.append({
            "data_type": DATA_TYPE,
            "data": mapped_data,
        })

    return results