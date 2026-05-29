import re
from typing import Any
from src.models.schemas import IncomingContact
from src.models.db import Contact

def compute_dedup_key(contact: IncomingContact | Contact) -> str | None:
    """
    Computes the DedupKey based on the specified rules:
    1. Lowercased, trimmed email if present.
    2. Fallback: name:<lower name>|phone:<digits only>.
    3. Return None if neither can be constructed.
    """
    email = contact.primary_email
    if email and email.strip():
        return email.strip().lower()

    name = contact.full_name
    phone = contact.phone
    
    if not name or not phone:
        return None
    
    clean_name = name.strip().lower()
    clean_phone = re.sub(r"\D", "", phone)
    
    if not clean_name or not clean_phone:
        return None
        
    return f"name:{clean_name}|phone:{clean_phone}"

def merge_contact_data(existing: Contact, incoming: IncomingContact) -> bool:
    """
    Merges incoming data into existing contact.
    Returns True if any field was changed.
    """
    changed = False
    
    # Scalar fields: keep existing if non-empty, otherwise fill from incoming
    fields = ["full_name", "primary_email", "phone", "job_title", "company_name"]
    for field in fields:
        existing_val = getattr(existing, field)
        incoming_val = getattr(incoming, field)
        
        if not existing_val and incoming_val:
            setattr(existing, field, incoming_val)
            changed = True

    # Shallow merge custom_fields
    if incoming.custom_fields:
        original_custom = existing.custom_fields.copy()
        existing.custom_fields.update(incoming.custom_fields)
        if existing.custom_fields != original_custom:
            changed = True
            
    return changed