import logging
from typing import Any, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def validate_and_normalize_email(email_str: Optional[str]) -> Optional[str]:
    """
    Validates an email string using the same rules as the host.
    Returns lowercased and trimmed email if valid, else None.
    """
    if not email_str:
        return None
    
    trimmed = email_str.strip()
    if not trimmed:
        return None

    try:
        # Check validity without deliverability/DNS checks per contract
        email_info = validate_email(trimmed, check_deliverability=False)
        return email_info.normalized.lower()
    except EmailNotValidError:
        return None

def map_contact(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Implements SugarCRM Contact -> IncomingContact mapping contract.
    
    Raises ValueError if:
    - id is missing or empty.
    - full_name cannot be derived.
    """
    # 1. Provider ID and External ID
    external_id = raw.get("id")
    if not external_id:
        raise ValueError("SugarCRM record missing 'id'")
    
    # 2. Primary Email Selection
    selected_email: Optional[str] = None
    email_list = raw.get("email")
    
    if isinstance(email_list, list) and email_list:
        # Try to find primary
        for entry in email_list:
            if entry.get("primary_address"):
                selected_email = entry.get("email_address")
                break
        
        # Fallback to first non-empty
        if not selected_email:
            for entry in email_list:
                if entry.get("email_address"):
                    selected_email = entry.get("email_address")
                    break

    # Fallback to email1
    if not selected_email:
        selected_email = raw.get("email1")

    # 3. Email Validation
    primary_email = validate_and_normalize_email(selected_email)
    if selected_email and not primary_email:
        logger.warning(
            f"SugarCRM record '{external_id}' has invalid email address: {selected_email}"
        )

    # 4. Full Name Derivation
    full_name: Optional[str] = None
    
    # Rule 1: full_name or name
    fn_val = raw.get("full_name") or raw.get("name")
    if fn_val and fn_val.strip():
        full_name = fn_val.strip()
    
    # Rule 2: first + last
    if not full_name:
        first = (raw.get("first_name") or "").strip()
        last = (raw.get("last_name") or "").strip()
        joined = f"{first} {last}".strip()
        if joined:
            full_name = joined
            
    # Rule 3: primary email fallback
    if not full_name and selected_email and selected_email.strip():
        full_name = selected_email.strip()
        
    if not full_name:
        raise ValueError(f"SugarCRM record '{external_id}' has no derivable full_name")

    # 5. Other fields
    phone_work = raw.get("phone_work")
    phone_mobile = raw.get("phone_mobile")
    phone = (phone_work if phone_work and phone_work.strip() else phone_mobile)
    if phone:
        phone = phone.strip() or None
    else:
        phone = None

    job_title = raw.get("title")
    if job_title:
        job_title = job_title.strip() or None
    
    company_name = raw.get("account_name")
    if company_name:
        company_name = company_name.strip() or None

    # 6. Custom Fields
    # Provenance fields copied verbatim
    custom_fields = {}
    for k in ["date_entered", "date_modified"]:
        if raw.get(k) is not None:
            custom_fields[k] = raw[k]

    # Return normalized IncomingContact dict
    return {
        "provider_id": "sugarcrm",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }