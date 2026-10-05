from typing import Any, Dict, List, Optional

def _get_first_value(values: Dict[str, List[Dict[str, Any]]], key: str) -> Optional[Dict[str, Any]]:
    """Helper to safely get the first entry of an attribute array."""
    entries = values.get(key)
    if not entries or not isinstance(entries, list) or len(entries) == 0:
        return None
    return entries[0]

def map_attio_person_to_contact(person: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps Attio PersonRecord to host Contact data shape.
    Follows rules in resources/attio/contact-mapping.md.
    """
    values = person.get("values", {})
    
    # external_id derivation
    external_id = person.get("id", {}).get("record_id")

    # full_name derivation
    full_name = ""
    name_val = _get_first_value(values, "name")
    if name_val:
        fn_field = name_val.get("full_name")
        if fn_field:
            full_name = fn_field.strip()
        else:
            first = (name_val.get("first_name") or "").strip()
            last = (name_val.get("last_name") or "").strip()
            full_name = f"{first} {last}".strip()

    # primary_email derivation
    primary_email = None
    email_val = _get_first_value(values, "email_addresses")
    if email_val:
        email_str = email_val.get("email_address")
        if email_str:
            primary_email = email_str.strip().lower()

    # job_title
    job_title = None
    job_val = _get_first_value(values, "job_title")
    if job_val:
        job_title = job_val.get("value")

    # custom_fields
    company_val = _get_first_value(values, "company")
    phone_val = _get_first_value(values, "phone_numbers")
    linkedin_val = _get_first_value(values, "linkedin")
    desc_val = _get_first_value(values, "description")

    custom_fields = {
        "company_record_id": company_val.get("target_record_id") if company_val else None,
        "phone_number": phone_val.get("phone_number") if phone_val else None,
        "linkedin": linkedin_val.get("value") if linkedin_val else None,
        "description": desc_val.get("value") if desc_val else None
    }

    return {
        "provider_id": "attio",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": None,
        "custom_fields": custom_fields
    }