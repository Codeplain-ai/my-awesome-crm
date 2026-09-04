import logging
from typing import Any, Callable, Dict, List
from .client import PipedriveClient
from .mapper import map_pipedrive_person

logger = logging.getLogger(__name__)

# Module level attribute for default data type
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Integration entry point for Pipedrive.
    Fetches Persons from Pipedrive and maps them to Contact records.
    """
    client = PipedriveClient()
    produced_records = []
    
    start = 0
    limit = 100
    has_more = True

    while has_more:
        try:
            page_data = client.list_persons(start=start, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch page from Pipedrive at start={start}: {str(e)}")
            raise

        persons = page_data.get("data") or []
        
        for person in persons:
            try:
                # Every integration's fetch applies a skip-and-log policy
                mapped_data = map_pipedrive_person(person)
                produced_records.append({
                    "data_type": "contact",
                    "data": mapped_data
                })
            except ValueError as ve:
                person_id = person.get("id", "unknown")
                logger.warning(f"Skipping Pipedrive person {person_id}: {str(ve)}")
            except Exception as e:
                # Re-raise unexpected mapping errors to fail the batch
                raise

        # Handle pagination
        pagination = page_data.get("additional_data", {}).get("pagination", {})
        has_more = pagination.get("more_items_in_collection", False)
        if has_more:
            start = pagination.get("next_start")
            if start is None:
                has_more = False
        else:
            has_more = False

    return produced_records