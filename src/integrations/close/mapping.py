import logging
from typing import Any, Dict, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def map_close_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements the CloseContactMapping contract.
    Converts a raw Close contact dict into an IncomingContact dict.
    """
    external_id = raw.get("id")
    if not external_id:
        raise ValueError("Close record is missing 'id'")

    # 1. Full Name derivation
    name = (raw.get("name") or "").strip()
    
    emails = raw.get("emails") or []
    first_email_val = ""
    if emails and isinstance(emails, list) and len(emails) > 0:
        first_email_val = (emails[0].get("email") or "").strip()

    full_name = ""
    if name:
        full_name = name
    elif first_email_val:
        full_name = first_email_val
    
    if not full_name:
        raise ValueError(f"Close record {external_id} has no derivable full_name")

    # 2. Primary Email validation
    primary_email: Optional[str] = None
    if first_email_val:
        try:
            # check_deliverability=False as per requirements
            valid = validate_email(first_email_val, check_deliverability=False)
            primary_email = valid.normalized.lower()
        except EmailNotValidError:
            logger.warning(
                f"Close contact {external_id} has invalid email format: {first_email_val}"
            )
            primary_email = None

    # 3. Phone (first non-empty)
    phone: Optional[str] = None
    phones = raw.get("phones") or []
    if phones and isinstance(phones, list):
        for p in phones:
            p_val = (p.get("phone") or "").strip()
            if p_val:
                phone = p_val
                break

    # 4. Job Title and Company
    job_title = (raw.get("title") or "").strip() or None
    
    # company_name: the docs say it's on the record if available, 
    # but based on mapping rules we check for a lead/org display name.
    # OpenApi shows 'display_name' is derived from 'name', we'll check if a 
    # specific 'company' or similar field exists but mapping says "parent lead/org name".
    # In Close, the 'lead_id' is the primary link.
    company_name = (raw.get("company_name") or "").strip() or None

    # 5. Custom Fields (provenance)
    # Mapping rules: lead_id, organization_id, date_created, date_updated
    custom_fields = {}
    for field in ["lead_id", "organization_id", "date_created", "date_updated"]:
        val = raw.get(field)
        if val is not None:
            custom_fields[field] = val

    return {
        "provider_id": "close",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }