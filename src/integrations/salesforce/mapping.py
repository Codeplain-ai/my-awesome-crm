from typing import Any

def map_contact_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Salesforce Contact record to the host's conventional contact shape.
    Implementation of [resource]resources/salesforce/contact-mapping.md
    """
    # provider_id: Always 'salesforce'
    # external_id: record Id
    external_id = record.get("Id")

    # full_name derivation
    name_field = record.get("Name")
    if name_field:
        full_name = name_field.strip()
    else:
        first = (record.get("FirstName") or "").strip()
        last = (record.get("LastName") or "").strip()
        full_name = f"{first} {last}".strip()

    # primary_email
    email_val = record.get("Email")
    primary_email = email_val.strip().lower() if email_val else None

    # job_title
    job_title = record.get("Title") or None

    # company_name
    account = record.get("Account")
    company_name = None
    if isinstance(account, dict):
        company_name = account.get("Name") or None

    # custom_fields rules: filter out consumed keys and attributes metadata
    consumed_keys = {"Id", "Name", "FirstName", "LastName", "Email", "Title", "Account", "attributes"}
    custom_fields = {}
    for k, v in record.items():
        if k in consumed_keys:
            continue
        # Ensure we don't copy nested attributes or nulls if they were metadata
        if k == "attributes":
            continue
        custom_fields[k] = v

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }