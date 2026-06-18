import logging
from typing import Any
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def _get_field_value(fields: dict[str, Any], key: str) -> str | None:
    """
    Helper to extract the first entry's value for a Nimble field key.
    Treats missing/empty values as None.
    """
    entries = fields.get(key)
    if not entries or not isinstance(entries, list) or len(entries) == 0:
        return None
    
    val = entries[0].get("value")
    if val is None:
        return None
    
    val = str(val).strip()
    return val if val else None

def map_nimble_contact(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Implements NimbleContactMapping logic to convert raw Nimble record to IncomingContact.
    """
    external_id = raw.get("id")
    if not external_id:
        raise ValueError("Nimble record is missing required 'id'")

    fields = raw.get("fields", {})
    
    # 1. full_name derivation
    first_name = _get_field_value(fields, "first name") or ""
    last_name = _get_field_value(fields, "last name") or ""
    joined_name = f"{first_name} {last_name}".strip()
    
    raw_email = _get_field_value(fields, "email")
    raw_company = _get_field_value(fields, "company")
    
    full_name = None
    if joined_name:
        full_name = joined_name
    elif raw_email:
        full_name = raw_email
    elif raw_company:
        full_name = raw_company
    
    if not full_name:
        raise ValueError(f"Could not derive full_name for Nimble contact {external_id}")

    # 2. primary_email validation
    primary_email = None
    if raw_email:
        email_candidate = raw_email.lower()
        try:
            # check_deliverability=False as per requirements
            validate_email(email_candidate, check_deliverability=False)
            primary_email = email_candidate
        except EmailNotValidError:
            logger.warning(
                f"Contact {external_id} has invalid email format: {raw_email}. Mapping email to None."
            )
            primary_email = None

    # 3. Custom fields (record_type only)
    custom_fields = {}
    record_type = raw.get("record_type")
    if record_type:
        custom_fields["record_type"] = record_type

    return {
        "provider_id": "nimble",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": _get_field_value(fields, "phone"),
        "job_title": _get_field_value(fields, "title"),
        "company_name": raw_company,
        "custom_fields": custom_fields
    }