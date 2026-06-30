from typing import Any, Dict, List

def map_close_contact(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements :CloseContactMapping: as defined in contact-mapping.md.
    """
    # 1. External IDs and Provider ID
    external_id = source.get("id")
    
    # 2. Emails extraction
    emails: List[Dict[str, Any]] = source.get("emails") or []
    first_email_raw = ""
    primary_email = None
    
    if emails and isinstance(emails, list):
        first_entry = emails[0]
        if isinstance(first_entry, dict):
            email_val = first_entry.get("email")
            if email_val:
                first_email_raw = str(email_val)
                primary_email = first_email_raw.strip().lower()

    # 3. full_name derivation
    # Rule 1: The name value, trimmed
    full_name = (source.get("name") or "").strip()
    
    # Rule 2: Otherwise the first emails[] entry's email value, trimmed
    if not full_name:
        full_name = first_email_raw.strip()
    
    # Rule 3: Otherwise an empty string (already handled by default)

    # 4. Job Title
    job_title = (source.get("title") or "").strip() or None

    # 5. Company Name (Parent Lead/Org Name)
    # The requirement states "lead or organization display name if available on the record"
    # In Close Contact records, 'display_name' is a Close-generated field often for the contact,
    # but the mapping spec specifically notes "lead or organization display name".
    # Since we don't have the Lead object, we look for 'company_name' if it exists or 
    # use the contact's 'display_name' as a best-effort fallback if appropriate, 
    # but the spec suggests looking for parent info.
    # Given the openapi.yaml, we don't see a 'lead_name' field, so we return None 
    # unless a field like 'company' or similar is present (not in schema).
    # Re-reading: "the lead or organization display name if available on the record".
    company_name = source.get("company_name") or source.get("organization_name") or None

    # 6. custom_fields
    # Capture lead_id, organization_id, date_created, date_updated
    custom_fields = {}
    for field in ["lead_id", "organization_id", "date_created", "date_updated"]:
        val = source.get(field)
        if val is not None:
            custom_fields[field] = val

    return {
        "provider_id": "close",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }