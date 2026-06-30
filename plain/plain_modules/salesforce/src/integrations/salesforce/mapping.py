import logging
from typing import Any

logger = logging.getLogger(__name__)

def map_account(record: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a raw Salesforce Account record to the conventional host account shape.
    Follows rules defined in resources/salesforce/account-mapping.md.
    """
    # 1. External ID
    external_id = record.get("Id")

    # 2. Name
    # Rule: stripped; empty string if missing.
    name = record.get("Name")
    if name and isinstance(name, str):
        name = name.strip()
    else:
        name = ""

    # 3. Website, Phone, Industry
    # Rule: value or None if missing/empty.
    def get_clean_str(key: str) -> Any:
        val = record.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
        return None

    website = get_clean_str("Website")
    phone = get_clean_str("Phone")
    industry = get_clean_str("Industry")

    # 4. custom_fields
    consumed_keys = {"Id", "Name", "Website", "Phone", "Industry", "attributes"}
    custom_fields = {
        k: v for k, v in record.items()
        if k not in consumed_keys
    }

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "name": name,
        "website": website,
        "phone": phone,
        "industry": industry,
        "custom_fields": custom_fields,
    }


def map_contact(record: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a raw Salesforce Contact record to the conventional host contact shape.
    Follows rules defined in resources/salesforce/contact-mapping.md.
    """
    # 1. External ID
    external_id = record.get("Id")

    # 2. full_name derivation
    # Rule: Name stripped, or FirstName + LastName joined, or empty string.
    full_name = ""
    name_field = record.get("Name")
    if name_field and isinstance(name_field, str) and name_field.strip():
        full_name = name_field.strip()
    else:
        first_name = (record.get("FirstName") or "").strip()
        last_name = (record.get("LastName") or "").strip()
        parts = [p for p in [first_name, last_name] if p]
        full_name = " ".join(parts)

    # 3. primary_email
    # Rule: Lowercased and trimmed. Empty/None maps to None.
    email_val = record.get("Email")
    primary_email = None
    if email_val and isinstance(email_val, str) and email_val.strip():
        primary_email = email_val.strip().lower()

    # 4. phone
    # Rule: Phone, else MobilePhone, else None.
    phone = record.get("Phone")
    if not (phone and isinstance(phone, str) and phone.strip()):
        phone = record.get("MobilePhone")
    
    if not (phone and isinstance(phone, str) and phone.strip()):
        phone = None
    else:
        phone = phone.strip()

    # 5. job_title
    job_title = record.get("Title")
    if not (job_title and isinstance(job_title, str) and job_title.strip()):
        job_title = None
    else:
        job_title = job_title.strip()

    # 6. company_name
    # Rule: Account.Name nested.
    company_name = None
    account_obj = record.get("Account")
    if isinstance(account_obj, dict):
        acc_name = account_obj.get("Name")
        if acc_name and isinstance(acc_name, str) and acc_name.strip():
            company_name = acc_name.strip()

    # 7. custom_fields
    # Rule: Non-consumed keys, excluding 'attributes'.
    consumed_keys = {
        "Id", "Name", "FirstName", "LastName", "Email", 
        "Phone", "MobilePhone", "Title", "Account", "attributes"
    }
    custom_fields = {
        k: v for k, v in record.items() 
        if k not in consumed_keys
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