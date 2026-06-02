from typing import Any

def hubspot_contact_to_incoming(hs_contact: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a HubSpot CRM v3 Contact object to an IncomingContact dict.
    
    :param hs_contact: A dict representing a HubSpot Contact (SimplePublicObject).
    :raises ValueError: If the ID is missing or a full_name cannot be derived.
    :return: An IncomingContact dict.
    """
    external_id = hs_contact.get("id")
    if not external_id:
        raise ValueError("HubSpot contact is missing the required 'id' field.")

    properties = hs_contact.get("properties", {})
    
    # 1. Map Full Name
    # Rule: firstname + lastname joined by space, stripped.
    first_name = (properties.get("firstname") or "").strip()
    last_name = (properties.get("lastname") or "").strip()
    
    full_name = f"{first_name} {last_name}".strip()
    
    # Fallback Rule: If both empty, use email local-part.
    if not full_name:
        email = properties.get("email") or ""
        if email and "@" in email:
            full_name = email.split("@")[0]
            
    if not full_name:
        raise ValueError(
            f"Could not determine a non-empty full_name for HubSpot contact {external_id}. "
            "Both name fields and email fallback are empty."
        )

    # 2. Map Scalar Fields
    primary_email = (properties.get("email") or "").strip().lower() or None
    phone = (properties.get("phone") or "").strip() or None
    job_title = (properties.get("jobtitle") or "").strip() or None
    company_name = (properties.get("company") or "").strip() or None

    # 3. Map Custom Fields
    # Capture keys not in the unified schema set: {firstname, lastname, email, phone, jobtitle, company}
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