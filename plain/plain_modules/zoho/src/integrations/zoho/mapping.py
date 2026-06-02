from typing import Any, Dict, Optional

def zoho_contact_to_incoming(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Zoho CRM Contact record to the unified IncomingContact schema.
    """
    external_id = record.get("id")
    if not external_id:
        raise ValueError("Zoho record is missing the required 'id' field.")
    
    # Map full_name
    full_name = record.get("Full_Name")
    if not full_name:
        first = (record.get("First_Name") or "").strip()
        last = (record.get("Last_Name") or "").strip()
        full_name = f"{first} {last}".strip()
    
    if not full_name:
        raise ValueError(f"Zoho record {external_id} is missing a valid name.")

    # Map primary_email
    email = record.get("Email")
    primary_email = email.strip().lower() if email and email.strip() else None

    # Map phone
    phone = record.get("Phone") or None

    # Map job_title
    job_title = record.get("Title") or None

    # Map company_name (Account_Name logic)
    account_name = record.get("Account_Name")
    company_name = None
    if isinstance(account_name, dict):
        company_name = account_name.get("name")
    elif isinstance(account_name, str) and account_name.strip():
        company_name = account_name.strip()

    # Define consumed keys for custom_fields extraction
    consumed_keys = {
        "id", "Full_Name", "First_Name", "Last_Name", 
        "Email", "Phone", "Title", "Account_Name"
    }
    
    custom_fields = {
        k: v for k, v in record.items() if k not in consumed_keys
    }

    return {
        "provider_id": "zoho",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields,
    }