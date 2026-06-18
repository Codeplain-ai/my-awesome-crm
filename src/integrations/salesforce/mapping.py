import logging
from typing import Any, Dict, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def map_contact_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements the SalesforceContactMapping contract.
    Converts a raw Salesforce Contact record into an IncomingContact dict.
    """
    # 1. external_id mapping
    external_id = record.get("Id")
    if not external_id:
        raise ValueError("Salesforce record is missing required 'Id' field.")

    # 2. full_name derivation
    full_name: Optional[str] = None
    sf_name = record.get("Name")
    if sf_name and sf_name.strip():
        full_name = sf_name.strip()
    else:
        first = (record.get("FirstName") or "").strip()
        last = (record.get("LastName") or "").strip()
        combined = f"{first} {last}".strip()
        if combined:
            full_name = combined

    if not full_name:
        raise ValueError(f"Salesforce record {external_id} has no derivable name.")

    # 3. primary_email validation
    primary_email: Optional[str] = None
    raw_email = record.get("Email")
    if raw_email and raw_email.strip():
        email_to_check = raw_email.strip().lower()
        try:
            # check_deliverability=False as per requirements
            valid = validate_email(email_to_check, check_deliverability=False)
            primary_email = valid.normalized
        except EmailNotValidError:
            logger.warning(
                f"Contact {external_id} has invalid email: {raw_email}. Mapping to None."
            )
            primary_email = None

    # 4. phone mapping
    phone = (record.get("Phone") or record.get("MobilePhone") or None)

    # 5. job_title mapping
    job_title = (record.get("Title") or None)

    # 6. company_name mapping
    company_name: Optional[str] = None
    account = record.get("Account")
    if isinstance(account, dict):
        account_name = account.get("Name")
        if account_name and account_name.strip():
            company_name = account_name.strip()

    # 7. custom_fields and consumed keys
    consumed_keys = {
        "Id", "Name", "FirstName", "LastName", "Email", 
        "Phone", "MobilePhone", "Title", "Account", "attributes"
    }
    
    custom_fields = {}
    for key, value in record.items():
        if key not in consumed_keys:
            custom_fields[key] = value

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }