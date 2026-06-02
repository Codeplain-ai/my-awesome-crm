from typing import Any, Dict, List, Optional

def streak_contact_to_incoming(contact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Streak Contact record to the unified IncomingContact schema.
    """
    # 1. Provider and External ID
    external_id = contact.get("key")
    if not external_id:
        raise ValueError("Streak contact is missing the required 'key' field.")

    # 2. Full Name with fallbacks
    full_name = contact.get("fullName", "").strip()
    if not full_name:
        given = contact.get("givenName", "").strip()
        family = contact.get("familyName", "").strip()
        full_name = f"{given} {family}".strip()
    
    if not full_name:
        raise ValueError(f"Streak contact {external_id} is missing a valid name.")

    # 3. Helper for list fields (email/phone)
    def _pick_first(items: Optional[List[str]]) -> Optional[str]:
        if not items:
            return None
        for item in items:
            if item and item.strip():
                return item.strip()
        return None

    # 4. Field Mapping
    primary_email = _pick_first(contact.get("emailAddresses"))
    if primary_email:
        primary_email = primary_email.lower()
    
    phone = _pick_first(contact.get("phoneNumbers"))
    job_title = contact.get("title") or None
    company_name = contact.get("companyName") or None

    # 5. Custom Fields (everything not in the unified schema)
    consumed_keys = {
        "key", "fullName", "givenName", "familyName", 
        "emailAddresses", "phoneNumbers", "title", "companyName"
    }
    custom_fields = {k: v for k, v in contact.items() if k not in consumed_keys}

    return {
        "provider_id": "streak",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }