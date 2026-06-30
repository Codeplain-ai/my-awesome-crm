import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def map_pipedrive_person_to_contact(person: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure mapping function following [resource]resources/pipedrive/contact-mapping.md.
    Maps a Pipedrive Person record to a host-conventional Contact data dict.
    """
    # 1. External IDs
    external_id = str(person.get("id")) if person.get("id") is not None else None

    # 2. full_name derivation
    # Rule: 'name' field stripped, else 'first_name' + 'last_name' joined, else empty string.
    full_name = ""
    raw_name = person.get("name")
    if raw_name and isinstance(raw_name, str) and raw_name.strip():
        full_name = raw_name.strip()
    else:
        fn = person.get("first_name") or ""
        ln = person.get("last_name") or ""
        full_name = f"{fn} {ln}".strip()

    # 3. primary_email selection
    # Rule: primary flag true, else first entry, else None. Lowercased and trimmed.
    primary_email = None
    emails: List[Dict[str, Any]] = person.get("email") or []
    chosen_email_val = ""
    
    if emails:
        # Find primary
        primary_entry = next((e for e in emails if e.get("primary") is True), None)
        if not primary_entry:
            primary_entry = emails[0]
        
        chosen_email_val = primary_entry.get("value") or ""

    if chosen_email_val and isinstance(chosen_email_val, str):
        trimmed = chosen_email_val.strip().lower()
        primary_email = trimmed if trimmed else None

    # 4. job_title
    job_title = person.get("job_title") or None

    # 5. company_name
    # Rule: org_name string, else org_id.name, else None.
    company_name = person.get("org_name")
    if not (company_name and isinstance(company_name, str) and company_name.strip()):
        org_id_obj = person.get("org_id")
        if isinstance(org_id_obj, dict):
            company_name = org_id_obj.get("name")
        else:
            company_name = None
    
    if company_name and isinstance(company_name, str) and not company_name.strip():
        company_name = None

    # 6. custom_fields
    # Rule: capture everything not consumed (id, name, first_name, last_name, email, phone, job_title, org_id, org_name)
    consumed_keys = {
        "id", "name", "first_name", "last_name", "email", 
        "phone", "job_title", "org_id", "org_name"
    }
    custom_fields = {
        k: v for k, v in person.items() if k not in consumed_keys
    }

    return {
        "provider_id": "pipedrive",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }