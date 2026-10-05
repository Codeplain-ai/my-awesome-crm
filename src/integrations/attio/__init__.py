import logging
from typing import Any, Callable, List
from .client import AttioClient
from .mapping import map_attio_person_to_contact

# Provider identifier used by the host for storage source and matching.
PROVIDER_ID = "attio"
# Default data type for this integration.
DATA_TYPE = "contact"

logger = logging.getLogger(__name__)

def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Fetches person records from Attio and maps them to the host's contact format.

    Pagination is offset-based as per Attio v2 API. Each page retrieves up to 500 records.
    """
    client = AttioClient()
    all_records = []
    offset = 0
    limit = 500

    while True:
        try:
            page_data = client.query_people(offset=offset, limit=limit)
        except Exception as e:
            logger.error(f"Attio API request failed at offset {offset}: {str(e)}")
            raise

        records_in_page = page_data.get("data", [])
        for raw_record in records_in_page:
            external_id = raw_record.get("id", {}).get("record_id")
            try:
                mapped_contact = map_attio_person_to_contact(raw_record)
                all_records.append({
                    "data_type": DATA_TYPE,
                    "data": mapped_contact
                })
            except ValueError as ve:
                logger.warning(
                    f"Skipping Attio record {external_id}: {str(ve)}",
                    extra={"external_id": external_id}
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error mapping Attio record {external_id}: {str(e)}",
                    extra={"external_id": external_id, "error": str(e)}
                )
                # We re-raise unexpected errors to abort the batch per :plainImplementationReqs:
                logger.exception(f"Unexpected error mapping Attio record {external_id}")
                raise

        # Pagination logic: if we got fewer than the limit, it's the last page.
        if len(records_in_page) < limit:
            break
        
        offset += limit

    return all_records