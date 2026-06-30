from typing import Any, Callable, List

from .client import DynamicsClient
from .mapping import map_contact

__all__ = ["fetch", "DATA_TYPE"]

# The default data type for this integration
DATA_TYPE = "contact"


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Entry point for the Dynamics 365 integration.
    Pulls contacts from Dataverse and maps them to the host's Contact format.
    """
    client = DynamicsClient()
    raw_records = client.list_contacts()
    
    produced = []
    for raw in raw_records:
        mapped_data = map_contact(raw)
        produced.append({
            "data_type": DATA_TYPE,
            "data": mapped_data
        })
        
    return produced