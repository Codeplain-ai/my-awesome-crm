import logging
from typing import Any

logger = logging.getLogger(__name__)

def zendesk_sell_contact_to_incoming(contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Zendesk Sell Contact record (the 'data' object) to an IncomingContact dict.
    """
    external_id = contact.get("id")
    if external_id is None:
        raise ValueError("Zendesk Sell contact record is missing 'id'")
    
    external_id = str(external_id)

    # Full Name mapping: name OR first_name + last_name
    full_name = contact.get("name")
    if not full_name:
        first = (contact.get("first_name") or "").strip()
        last = (contact.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip()
    
    if not full_name:
        raise ValueError(f"Zendesk Sell contact {external_id} is missing a valid name")

    # Unified schema fields
    primary_email = contact.get("email")
    if primary_email:
        primary_email = primary_email.strip().lower()
    else:
        primary_email = None

    # Custom fields capture all non-unified top-level keys
    consumed_keys = {
        "id", "name", "first_name", "last_name", 
        "email", "phone", "title", "organization_name"
    }
    
    custom_fields = {
        k: v for k, v in contact.items() 
        if k not in consumed_keys
    }

    return {
        "provider_id": "zendesk_sell",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": contact.get("phone") or None,
        "job_title": contact.get("title") or None,
        "company_name": contact.get("organization_name") or None,
        "custom_fields": custom_fields
    }