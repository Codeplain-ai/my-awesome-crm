from typing import Any, Dict

def map_contact(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure mapping function for Zendesk Sell ContactRecord -> conventional contact shape.
    Follows [resource]resources/zendesk_sell/contact-mapping.md.
    """
    
    # external_id: id rendered as string, or None if missing/empty
    raw_id = source.get("id")
    external_id = str(raw_id) if raw_id is not None and str(raw_id).strip() != "" else None

    is_org = source.get("is_organization") is True
    
    # Values used for name derivation and fields
    name_val = (source.get("name") or "").strip()
    first_name = (source.get("first_name") or "").strip()
    last_name = (source.get("last_name") or "").strip()
    email_val = (source.get("email") or "").strip()

    # full_name derivation logic
    full_name = ""
    if is_org:
        if name_val:
            full_name = name_val
    else:
        # Person logic: join first and last name
        joined = f"{first_name} {last_name}".strip()
        if joined:
            full_name = joined
        elif name_val:
            full_name = name_val
        elif email_val:
            full_name = email_val

    # primary_email: email lowercased and trimmed
    primary_email = email_val.lower() if email_val else None

    # company_name: organization_name trimmed
    org_name = (source.get("organization_name") or "").strip()
    company_name = org_name if org_name else None

    # job_title: title trimmed
    title = (source.get("title") or "").strip()
    job_title = title if title else None

    # custom_fields: include source custom fields and provenance
    out_custom = {}
    source_custom = source.get("custom_fields")
    if isinstance(source_custom, dict):
        for k, v in source_custom.items():
            if v is not None:
                out_custom[k] = v

    provenance_keys = [
        "created_at", "updated_at", "contact_id", 
        "parent_organization_id", "is_organization"
    ]
    for pk in provenance_keys:
        val = source.get(pk)
        if val is not None:
            out_custom[pk] = val

    return {
        "provider_id": "zendesk_sell",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": out_custom
    }