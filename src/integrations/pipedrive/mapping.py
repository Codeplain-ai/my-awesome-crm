from typing import Any

def pipedrive_person_to_incoming(person: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Pipedrive Person record to an IncomingContact dictionary.
    
    :param person: Raw dictionary from Pipedrive /v1/persons API.
    :return: Dictionary matching the IncomingContact schema.
    :raises ValueError: If required fields (id, name) are missing or invalid.
    """
    provider_id = "pipedrive"
    
    # 1. External ID (Required)
    raw_id = person.get("id")
    if raw_id is None:
        raise ValueError("Pipedrive person is missing required field: id")
    external_id = str(raw_id)

    # 2. Full Name logic (Required)
    # Priority: 'name' field -> 'first_name' + 'last_name'
    full_name = (person.get("name") or "").strip()
    if not full_name:
        first_name = (person.get("first_name") or "").strip()
        last_name = (person.get("last_name") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
    
    if not full_name:
        raise ValueError(f"Pipedrive person {external_id} has no valid name, first_name, or last_name")

    # 3. Email Mapping (List of objects)
    primary_email = None
    emails = person.get("email") or []
    if isinstance(emails, list):
        # Try to find primary
        for entry in emails:
            if entry.get("primary") and entry.get("value"):
                primary_email = entry["value"].strip().lower()
                break
        # Fallback to first non-empty value
        if not primary_email:
            for entry in emails:
                if entry.get("value"):
                    primary_email = entry["value"].strip().lower()
                    break

    # 4. Phone Mapping (List of objects)
    phone = None
    phones = person.get("phone") or []
    if isinstance(phones, list):
        for entry in phones:
            if entry.get("primary") and entry.get("value"):
                phone = entry["value"].strip()
                break
        if not phone:
            for entry in phones:
                if entry.get("value"):
                    phone = entry["value"].strip()
                    break

    # 5. Scalar fields
    job_title = (person.get("job_title") or "").strip() or None
    company_name = (person.get("org_name") or "").strip() or None

    # 6. Custom Fields extraction
    # Exclude consumed fields
    consumed_keys = {
        "id", "name", "first_name", "last_name", "email", 
        "phone", "job_title", "org_name"
    }
    
    custom_fields = {
        k: v for k, v in person.items() 
        if k not in consumed_keys
    }

    return {
        "provider_id": provider_id,
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }