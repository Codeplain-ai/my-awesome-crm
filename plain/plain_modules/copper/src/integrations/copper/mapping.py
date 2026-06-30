import logging
from typing import Any

logger = logging.getLogger(__name__)

def map_copper_person_to_contact(person: dict[str, Any]) -> dict[str, Any]:
    """
    Implements CopperContactMapping: converts a Copper People record to a Contact dict.
    
    This function follows the mapping rules defined in resources/copper/contact-mapping.md.
    It is a pure function and does not raise exceptions for missing or malformed data
    in the source record.
    """
    # external_id: record id rendered as decimal string
    raw_id = person.get("id")
    external_id = str(raw_id) if raw_id is not None else None

    # full_name derivation
    # 1. name field stripped
    # 2. first_name + last_name
    # 3. empty string
    name = person.get("name")
    if name and name.strip():
        full_name = name.strip()
    else:
        first = person.get("first_name") or ""
        last = person.get("last_name") or ""
        full_name = f"{first} {last}".strip()

    # primary_email: first entry of emails[] where email is non-empty, lowercased and trimmed.
    primary_email = None
    emails = person.get("emails") or []
    for entry in emails:
        if isinstance(entry, dict):
            val = entry.get("email")
            if val and val.strip():
                primary_email = val.strip().lower()
                break

    # custom_fields: captures date_created and date_modified verbatim when present
    custom_fields = {}
    if person.get("date_created") is not None:
        custom_fields["date_created"] = person["date_created"]
    if person.get("date_modified") is not None:
        custom_fields["date_modified"] = person["date_modified"]

    return {
        "provider_id": "copper",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": person.get("title") or None,
        "company_name": person.get("company_name") or None,
        "custom_fields": custom_fields,
    }