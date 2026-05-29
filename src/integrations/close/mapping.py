from typing import Any, Dict, List, Optional

def close_contact_to_incoming(contact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Close Contact record to the unified IncomingContact schema.
    """
    external_id = contact.get("id")
    if not external_id:
        raise ValueError("Close contact record is missing 'id' field.")

    full_name = contact.get("name")
    if not full_name or not full_name.strip():
        raise ValueError(f"Close contact {external_id} is missing a non-empty 'name'.")

    # Mapping Emails: Prefer "office", then first available
    primary_email: Optional[str] = None
    emails: List[Dict[str, str]] = contact.get("emails", [])
    if emails:
        office_email = next((e["email"] for e in emails if e.get("type") == "office" and e.get("email")), None)
        if office_email:
            primary_email = office_email
        else:
            primary_email = next((e["email"] for e in emails if e.get("email")), None)
    
    if primary_email:
        primary_email = primary_email.strip().lower()

    # Mapping Phones: Prefer "office", then first available
    phone: Optional[str] = None
    phones: List[Dict[str, str]] = contact.get("phones", [])
    if phones:
        office_phone = next((p["phone"] for p in phones if p.get("type") == "office" and p.get("phone")), None)
        if office_phone:
            phone = office_phone
        else:
            phone = next((p["phone"] for p in phones if p.get("phone")), None)

    job_title = contact.get("title") or None

    # Identify fields already consumed for unified schema
    consumed_keys = {"id", "name", "emails", "phones", "title"}
    custom_fields = {k: v for k, v in contact.items() if k not in consumed_keys}

    return {
        "provider_id": "close",
        "external_id": str(external_id),
        "full_name": full_name.strip(),
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": None,  # Per spec, company/lead data is out of scope for this mapping
        "custom_fields": custom_fields,
    }