from typing import Any

def hubspot_contact_to_incoming(hs_contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a HubSpot CRM v3 Contact object to an IncomingContact dict.
    """
    external_id = hs_contact.get("id")
    if not external_id:
        raise ValueError("HubSpot contact is missing the required 'id' field.")

    properties = hs_contact.get("properties", {})
    
    # 1. Map Full Name
    first_name = (properties.get("firstname") or "").strip()
    last_name = (properties.get("lastname") or "").strip()
    
    full_name = f"{first_name} {last_name}".strip()
    
    if not full_name:
        # Fallback to email local-part
        email = properties.get("email") or ""
        if email and "@" in email:
            full_name = email.split("@")[0]
            
    if not full_name:
        raise ValueError(f"Could not determine a non-empty full_name for HubSpot contact {external_id}")

    # 2. Map Scalar Fields
    primary_email = (properties.get("email") or "").strip().lower() or None
    phone = properties.get("phone") or None
    job_title = properties.get("jobtitle") or None
    company_name = properties.get("company") or None

    # 3. Map Custom Fields
    # Capture keys not in the unified schema set
    consumed_keys = {"firstname", "lastname", "email", "phone", "jobtitle", "company"}
    custom_fields = {
        k: v for k, v in properties.items() 
        if k not in consumed_keys
    }

    return {
        "provider_id": "hubspot",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }