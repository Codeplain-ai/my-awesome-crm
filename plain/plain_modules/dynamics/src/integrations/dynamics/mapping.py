import logging
from typing import Any
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def dynamics_contact_to_incoming(contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Dynamics 365 contact record to an IncomingContact dict.
    
    :param contact: Raw dictionary from Dataverse Web API.
    :return: Normalized IncomingContact dictionary.
    :raises ValueError: If mandatory fields (contactid, full_name) are missing.
    """
    external_id = contact.get("contactid")
    if not external_id:
        raise ValueError("Dynamics contact is missing mandatory 'contactid'")

    # Full Name Logic
    full_name = (contact.get("fullname") or "").strip()
    if not full_name:
        first = (contact.get("firstname") or "").strip()
        last = (contact.get("lastname") or "").strip()
        full_name = f"{first} {last}".strip()
    
    if not full_name:
        raise ValueError(f"Dynamics contact {external_id} has no valid name fields")

    # Email Validation Logic
    primary_email = None
    raw_email = contact.get("emailaddress1")
    if raw_email:
        raw_email = raw_email.strip().lower()
        try:
            # check_deliverability=False as per requirements
            valid = validate_email(raw_email, check_deliverability=False)
            primary_email = valid.normalized
        except EmailNotValidError:
            logger.warning(
                "Contact %s has invalid emailaddress1: %s", 
                external_id, raw_email
            )
            primary_email = None

    # Phone selection
    phone = contact.get("telephone1") or contact.get("mobilephone") or None

    # Company Name via parentcustomerid_account
    company_name = None
    parent_account = contact.get("parentcustomerid_account")
    if isinstance(parent_account, dict):
        company_name = (parent_account.get("name") or "").strip() or None

    # Custom Fields logic
    consumed_keys = {
        "contactid", "fullname", "firstname", "lastname", 
        "emailaddress1", "telephone1", "mobilephone", 
        "jobtitle", "parentcustomerid_account"
    }
    
    custom_fields = {
        k: v for k, v in contact.items()
        if k not in consumed_keys and not k.startswith("@odata")
    }

    return {
        "provider_id": "dynamics",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": contact.get("jobtitle") or None,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }