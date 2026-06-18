import logging
from typing import Any, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def map_copper_contact(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a raw Copper People record to an IncomingContact dict.
    
    Follows [resource]resources/copper/contact-mapping.md contract.
    Raises ValueError for missing external_id or underivable full_name.
    """
    # 1. external_id derivation
    external_id_raw = raw.get("id")
    if external_id_raw is None or str(external_id_raw).strip() == "":
        raise ValueError("Copper record missing required field: id")
    external_id = str(external_id_raw)

    # 2. full_name derivation
    full_name: Optional[str] = None
    
    # Rule 1: name field
    name_field = raw.get("name")
    if name_field and isinstance(name_field, str) and name_field.strip():
        full_name = name_field.strip()
    
    # Rule 2: first_name + last_name
    if not full_name:
        first = (raw.get("first_name") or "").strip()
        last = (raw.get("last_name") or "").strip()
        combined = f"{first} {last}".strip()
        if combined:
            full_name = combined

    if not full_name:
        raise ValueError(f"Copper record {external_id} has no derivable full_name")

    # 3. primary_email validation
    primary_email: Optional[str] = None
    emails = raw.get("emails") or []
    for entry in emails:
        email_val = entry.get("email")
        if email_val and isinstance(email_val, str) and email_val.strip():
            candidate = email_val.strip().lower()
            try:
                # Host logic: deliverability/DNS checks disabled
                validate_email(candidate, check_deliverability=False)
                primary_email = candidate
                break
            except EmailNotValidError:
                logger.warning(
                    f"Skipping invalid email format for Copper contact {external_id}",
                    extra={"external_id": external_id, "invalid_email": candidate}
                )
                # Keep primary_email as None and stop or continue? 
                # Contract says: first non-empty email... but only when valid.
                # If first is invalid, we don't fallback to second; we map to None.
                break

    # 4. phone derivation
    phone: Optional[str] = None
    phone_numbers = raw.get("phone_numbers") or []
    for entry in phone_numbers:
        num = entry.get("number")
        if num and isinstance(num, str) and num.strip():
            phone = num.strip()
            break

    # 5. job_title and company_name
    job_title = raw.get("title") or None
    if job_title: job_title = str(job_title).strip() or None
    
    company_name = raw.get("company_name") or None
    if company_name: company_name = str(company_name).strip() or None

    # 6. custom_fields (provenance)
    custom_fields = {}
    for prov_key in ["date_created", "date_modified"]:
        if raw.get(prov_key) is not None:
            custom_fields[prov_key] = raw[prov_key]

    return {
        "provider_id": "copper",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }