from typing import Any, Dict, List, Optional

def get_field_value(fields: Dict[str, Any], key: str) -> Optional[str]:
    """
    Helper to extract the 'value' of the FIRST entry in a Nimble field array.
    Returns None if the key is missing, array is empty, or value is null/empty.
    """
    entries = fields.get(key)
    if not entries or not isinstance(entries, list) or len(entries) == 0:
        return None
    
    val = entries[0].get("value")
    if val is None:
        return None
    
    trimmed = str(val).strip()
    return trimmed if trimmed else None

def map_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements the Nimble Contact -> contact-data mapping contract.
    Ref: resources/nimble/contact-mapping.md
    """
    fields = raw.get("fields", {})
    
    # 1. Basic Fields
    external_id = raw.get("id")
    job_title = get_field_value(fields, "title")
    company_name = get_field_value(fields, "company")
    
    # 2. Email (Lowercased and trimmed)
    email_val = get_field_value(fields, "email")
    primary_email = email_val.lower() if email_val else None
    
    # 3. Full Name Derivation
    first_name = get_field_value(fields, "first name")
    last_name = get_field_value(fields, "last name")
    
    full_name = ""
    # Rule 1: First + Last
    name_parts = []
    if first_name: name_parts.append(first_name)
    if last_name: name_parts.append(last_name)
    
    if name_parts:
        full_name = " ".join(name_parts)
    
    # Rule 2: Email fallback
    if not full_name and email_val:
        full_name = email_val
        
    # Rule 3: Company fallback
    if not full_name and company_name:
        full_name = company_name
    
    # 4. Custom Fields
    custom_fields = {}
    record_type = raw.get("record_type")
    if record_type is not None:
        custom_fields["record_type"] = record_type

    return {
        "provider_id": "nimble",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }