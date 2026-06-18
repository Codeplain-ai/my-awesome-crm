import logging
from .mapper import map_zoho_contact
from .client import get_credentials, get_access_token, fetch_raw_contacts

logger = logging.getLogger(__name__)

__all__ = ["fetch_contacts"]

def fetch_contacts() -> list[dict]:
    """
    Integration entry point. Fetches contacts from Zoho CRM, 
    maps them, and handles per-record failures.
    """
    creds = get_credentials()
    token = get_access_token(creds)
    
    contacts = []
    for raw_record in fetch_raw_contacts(creds, token):
        try:
            mapped = map_zoho_contact(raw_record)
            contacts.append(mapped)
        except ValueError as e:
            record_id = raw_record.get("id", "unknown")
            logger.warning(f"Skipping Zoho record {record_id} due to mapping error: {str(e)}")
            continue
            
    return contacts