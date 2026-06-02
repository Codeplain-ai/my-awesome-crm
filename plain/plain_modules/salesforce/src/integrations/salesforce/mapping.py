from typing import Any

def salesforce_contact_to_incoming(sf_contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Salesforce Contact sObject dictionary to an IncomingContact dictionary.
    
    :param sf_contact: Raw dictionary from Salesforce REST API.
    :return: Dictionary matching the IncomingContact schema.
    :raises ValueError: If required fields are missing.
    """
    provider_id = "salesforce"
    
    # 1. External ID (Required)
    external_id = sf_contact.get("Id")
    if not external_id:
        raise ValueError("Salesforce contact is missing required field: Id")

    # 2. Full Name logic (Required)
    # Use 'Name' if present, otherwise build from FirstName and LastName
    full_name = sf_contact.get("Name")
    if not full_name:
        first_name = (sf_contact.get("FirstName") or "").strip()
        last_name = (sf_contact.get("LastName") or "").strip()
        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
    else:
        full_name = full_name.strip()
    
    if not full_name:
        raise ValueError(f"Salesforce contact {external_id} has no valid Name, FirstName, or LastName")

    # 3. Scalar fields with normalization
    primary_email = sf_contact.get("Email")
    if primary_email and primary_email.strip():
        primary_email = primary_email.strip().lower()
    else:
        primary_email = None

    phone = sf_contact.get("Phone") or None
    job_title = sf_contact.get("Title") or None
    
    # 4. Nested Company Name (Account.Name)
    company_name = None
    account = sf_contact.get("Account")
    if isinstance(account, dict):
        company_name = account.get("Name") or None

    # 5. Custom Fields extraction
    # Exclude fields already consumed and the Salesforce 'attributes' metadata
    consumed_keys = {
        "Id", "Name", "FirstName", "LastName", "Email", 
        "Phone", "Title", "Account", "attributes"
    }
    
    custom_fields = {
        k: v for k, v in sf_contact.items() 
        if k not in consumed_keys
    }

    return {
        "provider_id": provider_id,
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }