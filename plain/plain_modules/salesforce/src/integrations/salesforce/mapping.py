import logging
from typing import Any
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def salesforce_contact_to_incoming(contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Salesforce Contact REST API record to an IncomingContact dict.
    """
    # 1. external_id
    external_id = contact.get("Id")
    if not external_id or not isinstance(external_id, str):
        raise ValueError("Salesforce contact record is missing a valid 'Id'.")

    # 2. full_name
    full_name = (contact.get("Name") or "").strip()
    if not full_name:
        first = (contact.get("FirstName") or "").strip()
        last = (contact.get("LastName") or "").strip()
        full_name = f"{first} {last}".strip()

    if not full_name:
        raise ValueError(f"Salesforce contact {external_id} has no name fields.")

    # 3. primary_email
    raw_email = contact.get("Email")
    primary_email = None
    if raw_email:
        raw_email = raw_email.strip()
        try:
            # Match host logic: lowercased, trimmed, no DNS check.
            email_info = validate_email(raw_email, check_deliverability=False)
            primary_email = email_info.normalized.lower()
        except EmailNotValidError:
            logger.warning(
                "Salesforce contact %s has invalid email format: %s", 
                external_id, raw_email
            )
            primary_email = None

    # 4. phone
    phone = contact.get("Phone") or contact.get("MobilePhone") or None

    # 5. job_title
    job_title = contact.get("Title") or None

    # 6. company_name
    company_name = None
    account = contact.get("Account")
    if isinstance(account, dict):
        company_name = (account.get("Name") or "").strip() or None

    # 7. custom_fields (remaining keys)
    consumed_keys = {
        "Id", "Name", "FirstName", "LastName", "Email", 
        "Phone", "MobilePhone", "Title", "Account", "attributes"
    }
    custom_fields = {
        k: v for k, v in contact.items() 
        if k not in consumed_keys and not k.startswith("attributes")
    }

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }