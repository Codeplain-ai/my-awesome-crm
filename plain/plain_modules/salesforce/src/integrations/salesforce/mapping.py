from typing import Any

def map_contact(source_record: dict[str, Any]) -> dict[str, Any]:
    """
    Implements SalesforceContactMapping contract.
    Maps a raw Salesforce Contact record to a host-standard Contact data dict.
    """
    # 1. provider_id: Always 'salesforce'
    # 2. external_id: The record's Id
    external_id = source_record.get("Id")

    # 3. full_name derivation
    # Rule 1: Name field (stripped)
    name_field = source_record.get("Name")
    if name_field and isinstance(name_field, str) and name_field.strip():
        full_name = name_field.strip()
    else:
        # Rule 2: FirstName + LastName
        first_name = (source_record.get("FirstName") or "").strip()
        last_name = (source_record.get("LastName") or "").strip()
        joined = f"{first_name} {last_name}".strip()
        # Rule 3: Otherwise empty string
        full_name = joined if joined else ""

    # 4. primary_email
    email_val = source_record.get("Email")
    if email_val and isinstance(email_val, str) and email_val.strip():
        primary_email = email_val.strip().lower()
    else:
        primary_email = None

    # 5. phone
    # Phone when present and non-empty; otherwise MobilePhone; otherwise None.
    phone = source_record.get("Phone")
    if not (phone and isinstance(phone, str) and phone.strip()):
        phone = source_record.get("MobilePhone")
    
    if not (phone and isinstance(phone, str) and phone.strip()):
        phone = None
    else:
        phone = phone.strip()

    # 6. job_title
    job_title = source_record.get("Title")
    if not (job_title and isinstance(job_title, str) and job_title.strip()):
        job_title = None
    else:
        job_title = job_title.strip()

    # 7. company_name
    # Account.Name or None
    account = source_record.get("Account")
    company_name = None
    if isinstance(account, dict):
        acc_name = account.get("Name")
        if acc_name and isinstance(acc_name, str) and acc_name.strip():
            company_name = acc_name.strip()

    # 8. custom_fields
    # Every field not consumed and not API metadata (attributes).
    consumed_keys = {
        "Id", "Name", "FirstName", "LastName", "Email", 
        "Phone", "MobilePhone", "Title", "Account", "attributes"
    }
    
    custom_fields = {
        k: v for k, v in source_record.items() 
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