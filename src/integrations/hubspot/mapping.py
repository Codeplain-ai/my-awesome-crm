from typing import Any

def map_contact(record: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a HubSpot ContactRecord to the conventional contact shape.
    Follows the rules in resources/hubspot/contact-mapping.md.
    """
    properties = record.get("properties") or {}
    
    # full_name derivation
    # 1. Join firstname and lastname by a single space, treat empty/null as "", strip whitespace.
    first = (properties.get("firstname") or "").strip()
    last = (properties.get("lastname") or "").strip()
    full_name = " ".join(filter(None, [first, last]))

    # primary_email derivation
    # lowercased and trimmed. Missing/empty maps to None.
    email = properties.get("email")
    if email:
        primary_email = email.strip().lower()
        if not primary_email:
            primary_email = None
    else:
        primary_email = None

    return {
        "provider_id": "hubspot",
        "external_id": record.get("id"),
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": properties.get("jobtitle") or None,
        "company_name": properties.get("company") or None,
        "custom_fields": {}
    }
