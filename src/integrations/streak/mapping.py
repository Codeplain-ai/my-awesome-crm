import logging
from typing import Any
from email_validator import validate_email, EmailNotValidError
from src.models.schemas import IncomingContact

logger = logging.getLogger(__name__)

def map_streak_contact(raw: dict[str, Any]) -> IncomingContact:
    """
    Implements the StreakContactMapping contract.
    Converts a raw Streak ContactRecord dict into an IncomingContact.
    
    Raises ValueError for records that must be skipped (missing key or name).
    """
    # 1. external_id (key)
    external_id = raw.get("key")
    if not external_id or not str(external_id).strip():
        raise ValueError("Streak record missing required 'key'")

    # 2. full_name derivation
    full_name = None
    
    # Rule 1: fullName
    fn_field = raw.get("fullName")
    if fn_field and str(fn_field).strip():
        full_name = str(fn_field).strip()
    
    # Rule 2: givenName + familyName
    if not full_name:
        gn = str(raw.get("givenName") or "").strip()
        sn = str(raw.get("familyName") or "").strip()
        joined = f"{gn} {sn}".strip()
        if joined:
            full_name = joined

    # Rule 3: first email
    emails = raw.get("emailAddresses") or []
    if not full_name and emails:
        for email in emails:
            if email and str(email).strip():
                full_name = str(email).strip()
                break
    
    if not full_name:
        raise ValueError(f"Streak record {external_id} has no derivable full_name")

    # 3. primary_email validation
    primary_email = None
    if emails:
        first_email = None
        for e in emails:
            if e and str(e).strip():
                first_email = str(e).strip()
                break
        
        if first_email:
            try:
                # Validate using host's preferred logic (no DNS/deliverability checks)
                valid = validate_email(first_email, check_deliverability=False)
                primary_email = valid.normalized.lower()
            except EmailNotValidError:
                logger.warning(
                    f"Streak record {external_id} has invalid primary email: {first_email}"
                )
                primary_email = None

    # 4. phone
    phone = None
    phone_numbers = raw.get("phoneNumbers") or []
    for p in phone_numbers:
        if p and str(p).strip():
            phone = str(p).strip()
            break

    # 5. job_title
    job_title = raw.get("title")
    if job_title:
        job_title = str(job_title).strip() or None

    # 6. custom_fields
    custom_fields = {}
    for key in ["creationTimestamp", "lastSavedTimestamp"]:
        if key in raw and raw[key] is not None:
            custom_fields[key] = raw[key]

    return IncomingContact(
        provider_id="streak",
        external_id=str(external_id),
        full_name=full_name,
        primary_email=primary_email,
        phone=phone,
        job_title=job_title,
        company_name=None,
        custom_fields=custom_fields
    )