import logging
from typing import Any
from email_validator import validate_email, EmailNotValidError
from src.models.schemas import IncomingContact

logger = logging.getLogger(__name__)

def map_dynamics_contact(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Dynamics 365 contact record to an IncomingContact dict.
    
    Follows rules defined in resources/dynamics/contact-mapping.md.
    Raises ValueError for record-skipping conditions.
    """
    # 1. external_id validation
    external_id = raw.get("contactid")
    if not external_id:
        raise ValueError("Dynamics record missing 'contactid'")

    # 2. full_name derivation
    full_name = None
    if raw.get("fullname"):
        full_name = str(raw["fullname"]).strip()
    
    if not full_name:
        first = (raw.get("firstname") or "").strip()
        last = (raw.get("lastname") or "").strip()
        joined = f"{first} {last}".strip()
        if joined:
            full_name = joined
            
    if not full_name:
        raise ValueError(f"Dynamics contact {external_id} has no derivable full_name")

    # 3. primary_email validation
    primary_email = None
    raw_email = raw.get("emailaddress1")
    if raw_email and str(raw_email).strip():
        email_clean = str(raw_email).strip().lower()
        try:
            # Match host validation: check_deliverability=False
            valid = validate_email(email_clean, check_deliverability=False)
            primary_email = valid.normalized
        except EmailNotValidError:
            logger.warning(
                f"Dynamics contact {external_id} has invalid email: {raw_email}"
            )
            primary_email = None

    # 4. phone mapping
    phone = raw.get("telephone1") or raw.get("mobilephone") or None
    if phone:
        phone = str(phone).strip() or None

    # 5. job_title
    job_title = raw.get("jobtitle")
    if job_title:
        job_title = str(job_title).strip() or None

    # 6. company_name (from expanded parentcustomerid_account)
    company_name = None
    parent_account = raw.get("parentcustomerid_account")
    if isinstance(parent_account, dict):
        name = parent_account.get("name")
        if name:
            company_name = str(name).strip() or None

    # 7. custom_fields
    consumed_keys = {
        "contactid", "fullname", "firstname", "lastname", 
        "emailaddress1", "telephone1", "mobilephone", 
        "jobtitle", "parentcustomerid_account"
    }
    
    custom_fields = {}
    for key, value in raw.items():
        if key in consumed_keys:
            continue
        if key.startswith("@odata."):
            continue
        if "@" in key: # OData annotations
            continue
        custom_fields[key] = value

    return {
        "provider_id": "dynamics",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }