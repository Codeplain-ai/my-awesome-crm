import logging
from typing import Any

logger = logging.getLogger(__name__)

def copper_person_to_incoming(person: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Copper Person record to the unified IncomingContact schema.
    """
    external_id = person.get("id")
    if external_id is None:
        raise ValueError("Copper person record is missing 'id'")
    
    external_id = str(external_id)
    
    full_name = person.get("name")
    if not full_name or not full_name.strip():
        raise ValueError(f"Copper person {external_id} is missing a non-empty 'name'")

    # Email mapping: "work" first, then first available
    emails = person.get("emails", [])
    primary_email = None
    if emails:
        work_email = next((e["email"] for e in emails if e.get("category") == "work"), None)
        if work_email:
            primary_email = work_email
        else:
            primary_email = next((e["email"] for e in emails if e.get("email")), None)
    
    if primary_email:
        primary_email = primary_email.strip().lower()

    # Phone mapping: "work" first, then first available
    phones = person.get("phone_numbers", [])
    phone_val = None
    if phones:
        work_phone = next((p["number"] for p in phones if p.get("category") == "work"), None)
        if work_phone:
            phone_val = work_phone
        else:
            phone_val = next((p["number"] for p in phones if p.get("number")), None)

    # Standard fields
    job_title = person.get("title") or None
    company_name = person.get("company_name") or None

    # Custom fields: everything not in the unified schema
    consumed_keys = {"id", "name", "emails", "phone_numbers", "title", "company_name"}
    custom_fields = {k: v for k, v in person.items() if k not in consumed_keys}

    return {
        "provider_id": "copper",
        "external_id": external_id,
        "full_name": full_name.strip(),
        "primary_email": primary_email,
        "phone": phone_val,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }