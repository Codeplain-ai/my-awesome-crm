import logging
from typing import Any

logger = logging.getLogger(__name__)

CONSUMED_KEYS = {
    "Id",
    "Name",
    "FirstName",
    "LastName",
    "Email",
    "Title",
    "Account",
}

def map_contact_record(raw_record: dict[str, Any]) -> dict[str, Any]:
    """
    Implements SalesforceContactMapping contract.
    Converts a raw Salesforce Contact record into a standardized contact data dict.
    """
    # 1. external_id
    external_id = raw_record.get("Id")

    # 2. full_name derivation
    # Rule 1: Name field
    full_name = raw_record.get("Name")
    if full_name:
        full_name = full_name.strip()
    
    # Rule 2: FirstName + LastName
    if not full_name:
        first = raw_record.get("FirstName") or ""
        last = raw_record.get("LastName") or ""
        full_name = f"{first} {last}".strip()
    
    # Rule 3: Fallback to empty string
    if not full_name:
        full_name = ""

    # 3. primary_email
    email = raw_record.get("Email")
    primary_email = email.strip().lower() if email else None

    # 4. job_title
    job_title = raw_record.get("Title") or None

    # 5. company_name (Account.Name)
    company_name = None
    account = raw_record.get("Account")
    if isinstance(account, dict):
        company_name = account.get("Name") or None

    # 6. custom_fields
    # Exclude consumed keys and 'attributes' metadata
    custom_fields = {
        k: v for k, v in raw_record.items()
        if k not in CONSUMED_KEYS and k != "attributes"
    }

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }