import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PROVIDER_ID = "pipedrive"

def map_pipedrive_person(person: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Pipedrive Person record to the conventional Contact shape.
    Follows [resource]resources/pipedrive/contact-mapping.md.
    """
    external_id = str(person["id"]) if person.get("id") is not None else None
    
    # 1. full_name derivation
    name_val = (person.get("name") or "").strip()
    if name_val:
        full_name = name_val
    else:
        first = (person.get("first_name") or "").strip()
        last = (person.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip()

    # 2. primary_email selection
    emails = person.get("email") or []
    chosen_email = ""
    if emails:
        primary = next((e for e in emails if e.get("primary")), None)
        if not primary:
            primary = emails[0]
        chosen_email = (primary.get("value") or "").strip().lower()
    
    primary_email = chosen_email if chosen_email else None

    # 3. company_name derivation
    org_name_val = person.get("org_name")
    if org_name_val:
        company_name = org_name_val
    else:
        org_id_obj = person.get("org_id")
        if isinstance(org_id_obj, dict):
            company_name = org_id_obj.get("name")
        else:
            company_name = None

    # 4. job_title
    job_title = person.get("job_title") or None

    # 5. custom_fields
    consumed_keys = {"id", "name", "first_name", "last_name", "email", "job_title", "org_id", "org_name"}
    discarded_keys = {"phone"}
    
    custom_fields = {
        k: v for k, v in person.items() 
        if k not in consumed_keys and k not in discarded_keys
    }

    return {
        "provider_id": PROVIDER_ID,
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }