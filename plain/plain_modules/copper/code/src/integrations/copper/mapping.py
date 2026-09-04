from typing import Any, Dict, Optional

def map_copper_person_to_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Copper People record to the conventional 'contact' data shape.
    Follows [resource]resources/copper/contact-mapping.md.
    """
    
    # 1. external_id derivation
    raw_id = record.get("id")
    external_id: Optional[str] = None
    if raw_id is not None and str(raw_id).strip() != "":
        external_id = str(raw_id)

    # 2. full_name derivation
    name_field = (record.get("name") or "").strip()
    if name_field:
        full_name = name_field
    else:
        first = (record.get("first_name") or "").strip()
        last = (record.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip()

    # 3. primary_email derivation
    primary_email: Optional[str] = None
    emails = record.get("emails") or []
    for entry in emails:
        if isinstance(entry, dict):
            email_val = entry.get("email")
            if email_val and email_val.strip():
                primary_email = email_val.strip().lower()
                break

    # 4. job_title and company_name
    job_title = record.get("title") or None
    company_name = record.get("company_name") or None

    # 5. custom_fields (provenance timestamps)
    custom_fields = {}
    for key in ["date_created", "date_modified"]:
        val = record.get(key)
        if val is not None:
            custom_fields[key] = val

    return {
        "provider_id": "copper",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }