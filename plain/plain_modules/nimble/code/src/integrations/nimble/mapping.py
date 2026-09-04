import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_field_value(fields: Dict[str, List[Dict[str, Any]]], key: str) -> Optional[str]:
    """
    Extracts the 'value' of the FIRST entry in a field's array per contract.
    Treats as missing if key is absent, array empty, or value is empty/null.
    """
    entries = fields.get(key)
    if not entries or not isinstance(entries, list) or len(entries) == 0:
        return None
    
    first_entry = entries[0]
    if not isinstance(first_entry, dict):
        return None
        
    val = first_entry.get("value")
    if val is None:
        return None
        
    trimmed = str(val).strip()
    return trimmed if trimmed != "" else None

def map_contact(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Nimble ContactRecord to a host Contact shape.
    Follows [resource]resources/nimble/contact-mapping.md strictly.
    """
    fields = source.get("fields", {})
    
    # 1. External ID
    external_id = source.get("id")
    
    # 2. Extract specific fields for logic
    first_name = _get_field_value(fields, "first name")
    last_name = _get_field_value(fields, "last name")
    email = _get_field_value(fields, "email")
    company = _get_field_value(fields, "company")
    title = _get_field_value(fields, "title")

    # 3. full_name derivation
    full_name = ""
    # Rule 1: First + Last joined by space (stripped)
    if first_name or last_name:
        parts = []
        if first_name: parts.append(first_name)
        if last_name: parts.append(last_name)
        full_name = " ".join(parts).strip()
    
    # Rule 2: Email fallback
    if not full_name and email:
        full_name = email
    
    # Rule 3: Company fallback
    if not full_name and company:
        full_name = company
        
    # 4. primary_email (lowercased and trimmed)
    primary_email = email.lower() if email else None

    # 5. custom_fields
    # Captures record_type, excludes business fields used above and raw fields map/id.
    custom_fields = {}
    record_type = source.get("record_type")
    if record_type is not None:
        custom_fields["record_type"] = record_type

    return {
        "provider_id": "nimble",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": title,
        "company_name": company,
        "custom_fields": custom_fields
    }