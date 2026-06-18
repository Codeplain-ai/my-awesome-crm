import logging
from typing import Any, Dict
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

# Keys consumed by the mapping process; these are not added to custom_fields.
CONSUMED_KEYS = {
    "id",
    "name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "job_title",
    "org_id",
    "org_name",
}

def map_pipedrive_person(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure mapping function following [resource]resources/pipedrive/contact-mapping.md.
    
    Args:
        raw: A dictionary representing a Pipedrive Person record.
        
    Returns:
        An IncomingContact dictionary.
        
    Raises:
        ValueError: If id is missing/empty or full_name cannot be derived.
    """
    # 1. external_id
    ext_id = raw.get("id")
    if ext_id is None or str(ext_id).strip() == "":
        raise ValueError("Pipedrive record missing 'id'")
    external_id = str(ext_id)

    # 2. full_name derivation
    full_name = _derive_full_name(raw)
    if not full_name:
        raise ValueError(f"Pipedrive record {external_id} missing derivable name")

    # 3. primary_email derivation and validation
    primary_email = _derive_email(raw, external_id)

    # 4. phone derivation
    phone = _derive_phone(raw)

    # 5. company_name derivation
    company_name = _derive_company_name(raw)

    # 6. job_title
    job_title = raw.get("job_title") or None

    # 7. custom_fields
    custom_fields = {
        k: v for k, v in raw.items() 
        if k not in CONSUMED_KEYS
    }

    return {
        "provider_id": "pipedrive",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }

def _derive_full_name(raw: Dict[str, Any]) -> str | None:
    # Rule 1: 'name' field
    name = raw.get("name")
    if name and isinstance(name, str) and name.strip():
        return name.strip()
    
    # Rule 2: first_name + last_name
    fn = raw.get("first_name") or ""
    ln = raw.get("last_name") or ""
    combined = f"{fn} {ln}".strip()
    if combined:
        return combined
        
    return None

def _derive_email(raw: Dict[str, Any], external_id: str) -> str | None:
    emails = raw.get("email")
    if not emails or not isinstance(emails, list):
        return None

    # Find primary or first
    chosen_value = None
    primary_entry = next((e for e in emails if e.get("primary")), None)
    if primary_entry:
        chosen_value = primary_entry.get("value")
    elif emails:
        chosen_value = emails[0].get("value")

    if not chosen_value or not isinstance(chosen_value, str) or not chosen_value.strip():
        return None

    email_val = chosen_value.strip().lower()
    
    try:
        # Validate using same logic as host (deliverability checks disabled)
        valid = validate_email(email_val, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError:
        logger.warning(
            f"Pipedrive contact {external_id} has invalid email: {email_val}"
        )
        return None

def _derive_phone(raw: Dict[str, Any]) -> str | None:
    phones = raw.get("phone")
    if not phones or not isinstance(phones, list):
        return None

    primary_entry = next((p for p in phones if p.get("primary")), None)
    if primary_entry and primary_entry.get("value"):
        return str(primary_entry.get("value"))
    
    if phones and phones[0].get("value"):
        return str(phones[0].get("value"))
        
    return None

def _derive_company_name(raw: Dict[str, Any]) -> str | None:
    # Rule: org_name, else org_id.name
    org_name = raw.get("org_name")
    if org_name and isinstance(org_name, str) and org_name.strip():
        return org_name.strip()
    
    org_id = raw.get("org_id")
    if isinstance(org_id, dict):
        name = org_id.get("name")
        if name and isinstance(name, str) and name.strip():
            return name.strip()
            
    return None