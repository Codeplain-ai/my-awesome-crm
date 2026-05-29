from typing import Any

def sugarcrm_contact_to_incoming(contact: dict[str, Any]) -> dict[str, Any]:
    """
    Converts a SugarCRM Contact record into an IncomingContact dict.
    
    Field mapping rules:
    - provider_id: 'sugarcrm'
    - external_id: 'id' (required)
    - full_name: 'full_name' or 'first_name' + 'last_name' (required)
    - primary_email: 'email1' (lowercased)
    - phone: 'phone_work' or 'phone_mobile'
    - job_title: 'title'
    - company_name: 'account_name'
    - custom_fields: All other unconsumed top-level keys
    """
    external_id = contact.get("id")
    if not external_id:
        raise ValueError("SugarCRM record is missing 'id'")

    # Full Name logic
    full_name = contact.get("full_name", "").strip()
    if not full_name:
        first_name = contact.get("first_name", "").strip()
        last_name = contact.get("last_name", "").strip()
        full_name = f"{first_name} {last_name}".strip()
    
    if not full_name:
        raise ValueError(f"SugarCRM record {external_id} is missing a name")

    # Primary Email
    primary_email = contact.get("email1", "").strip().lower() or None

    # Phone logic: phone_work fallback to phone_mobile
    phone = contact.get("phone_work") or contact.get("phone_mobile") or None

    # Mapping basic fields
    incoming = {
        "provider_id": "sugarcrm",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": contact.get("title") or None,
        "company_name": contact.get("account_name") or None,
        "custom_fields": {}
    }

    # Custom fields: everything not consumed
    consumed_keys = {
        "id", "full_name", "first_name", "last_name", 
        "email1", "phone_work", "phone_mobile", "title", "account_name"
    }
    
    for key, value in contact.items():
        if key not in consumed_keys:
            incoming["custom_fields"][key] = value

    return incoming