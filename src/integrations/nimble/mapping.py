import logging
from typing import Any

logger = logging.getLogger(__name__)

def _first_value(contact: dict, key: str) -> str | None:
    """
    Returns the value of the first entry in contact["fields"][key] whose value 
    is non-empty and trimmed. Returns None if key is missing or all entries are empty.
    """
    fields = contact.get("fields", {})
    entries = fields.get(key, [])
    
    for entry in entries:
        val = entry.get("value")
        if val and isinstance(val, str):
            trimmed = val.strip()
            if trimmed:
                return trimmed
    return None

def nimble_contact_to_incoming(contact: dict) -> dict[str, Any]:
    """
    Converts a Nimble Contact record into an IncomingContact dict.
    """
    external_id = contact.get("id")
    if not external_id:
        raise ValueError("Nimble contact is missing required 'id' field")

    first_name = _first_value(contact, "first name")
    last_name = _first_value(contact, "last name")
    
    name_parts = []
    if first_name:
        name_parts.append(first_name)
    if last_name:
        name_parts.append(last_name)
        
    full_name = " ".join(name_parts).strip()
    
    if not full_name:
        raise ValueError(f"Nimble contact {external_id} has no valid name")

    primary_email = _first_value(contact, "email")
    if primary_email:
        primary_email = primary_email.lower()

    phone = _first_value(contact, "phone")
    job_title = _first_value(contact, "title")
    company_name = _first_value(contact, "company name")

    # Build custom_fields
    # Start with top-level fields excluding 'id' and 'fields'
    custom_fields = {k: v for k, v in contact.items() if k not in ("id", "fields")}
    
    # Process 'fields' sub-dict
    consumed_keys = {"first name", "last name", "email", "phone", "title", "company name"}
    original_fields = contact.get("fields", {})
    unconsumed_fields = {k: v for k, v in original_fields.items() if k not in consumed_keys}
    
    custom_fields["fields"] = unconsumed_fields

    return {
        "provider_id": "nimble",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }