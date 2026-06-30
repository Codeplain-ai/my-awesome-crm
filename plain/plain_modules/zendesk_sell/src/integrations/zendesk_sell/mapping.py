from typing import Any, Dict

def map_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements ZendeskSellContactMapping.
    Converts a raw Zendesk Sell Contact record (unwrapped 'data' object) 
    into a host-standard Contact data dict.
    """
    # 1. external_id derivation
    raw_id = raw.get("id")
    external_id = str(raw_id) if raw_id is not None and str(raw_id).strip() != "" else None

    # 2. full_name derivation
    is_org = raw.get("is_organization") is True
    full_name = ""
    
    name_val = (raw.get("name") or "").strip()
    first_name = (raw.get("first_name") or "").strip()
    last_name = (raw.get("last_name") or "").strip()
    email_val = (raw.get("email") or "").strip()

    if is_org:
        if name_val:
            full_name = name_val
    else:
        # Person logic
        joined_name = f"{first_name} {last_name}".strip()
        if joined_name:
            full_name = joined_name
        elif name_val:
            full_name = name_val
        elif email_val:
            full_name = email_val

    # 3. primary_email
    email_raw = raw.get("email")
    primary_email = email_raw.lower().strip() if email_raw and email_raw.strip() else None

    # 4. company_name
    org_name = raw.get("organization_name")
    company_name = org_name.strip() if org_name and org_name.strip() else None

    # 5. custom_fields
    # Starts from existing custom_fields
    cf_source = raw.get("custom_fields") or {}
    custom_fields = {k: v for k, v in cf_source.items() if v is not None}
    
    # Add provenance fields
    provenance_keys = [
        "created_at", "updated_at", "contact_id", 
        "parent_organization_id", "is_organization"
    ]
    for pk in provenance_keys:
        val = raw.get(pk)
        if val is not None:
            custom_fields[pk] = val

    return {
        "provider_id": "zendesk_sell",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": raw.get("title") if raw.get("title") else None,
        "company_name": company_name,
        "custom_fields": custom_fields
    }