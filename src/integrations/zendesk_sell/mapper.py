import logging
from typing import Any, Dict, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def map_zendesk_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements :ZendeskSellContactMapping:.
    Converts a raw Zendesk Sell contact 'data' object into an IncomingContact dict.
    
    Raises:
        ValueError: If external_id is missing or full_name cannot be derived.
    """
    # 1. external_id derivation
    raw_id = data.get("id")
    if raw_id is None or str(raw_id).strip() == "":
        raise ValueError("Zendesk Sell contact missing required 'id'")
    external_id = str(raw_id)

    # 2. full_name derivation
    full_name = _derive_full_name(data)
    if not full_name:
        raise ValueError(f"Zendesk Sell contact {external_id} has no derivable full_name")

    # 3. primary_email validation
    primary_email = _validate_email_field(data.get("email"), external_id)

    # 4. phone derivation (phone, else mobile)
    phone = data.get("phone") or data.get("mobile") or None

    # 5. basic fields
    job_title = data.get("title") or None
    company_name = (data.get("organization_name") or "").strip() or None

    # 6. custom_fields rules
    custom_fields = _build_custom_fields(data)

    return {
        "provider_id": "zendesk_sell",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }

def _derive_full_name(data: Dict[str, Any]) -> Optional[str]:
    # Rule 1: Organization name
    if data.get("is_organization") is True:
        val = (data.get("name") or "").strip()
        if val:
            return val

    # Rule 2: Person first + last
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    joined = f"{first} {last}".strip()
    if joined:
        return joined

    # Rule 3: Fallback to name field
    val = (data.get("name") or "").strip()
    if val:
        return val

    # Rule 4: Fallback to email
    val = (data.get("email") or "").strip()
    if val:
        return val

    return None

def _validate_email_field(email_str: Any, external_id: str) -> Optional[str]:
    if not email_str or not str(email_str).strip():
        return None
    
    email_val = str(email_str).strip()
    try:
        # Deliverability/DNS checks disabled to match host IncomingContact contract
        validated = validate_email(email_val, check_deliverability=False)
        return validated.normalized.lower()
    except EmailNotValidError:
        logger.warning(
            f"Zendesk Sell contact {external_id} has invalid email format: {email_val}"
        )
        return None

def _build_custom_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    # Start with actual custom fields from Sell
    result = dict(data.get("custom_fields") or {})
    
    # Add provenance fields
    provenance_keys = [
        "created_at", "updated_at", "contact_id", 
        "parent_organization_id", "is_organization"
    ]
    for key in provenance_keys:
        val = data.get(key)
        if val is not None:
            result[key] = val
            
    return result