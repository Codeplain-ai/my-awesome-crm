from typing import Any, Dict

def map_contact(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implementation of :CloseContactMapping:.
    Maps Close ContactRecord to conventional Contact shape.
    """
    emails = source.get("emails", [])
    first_email_obj = emails[0] if emails and isinstance(emails, list) else {}
    first_email_val = first_email_obj.get("email") if isinstance(first_email_obj, dict) else None

    # 1. full_name derivation
    # Rule: name trimmed, else first email trimmed, else empty string.
    full_name = ""
    raw_name = source.get("name")
    if raw_name and str(raw_name).strip():
        full_name = str(raw_name).strip()
    elif first_email_val and str(first_email_val).strip():
        full_name = str(first_email_val).strip()

    # 2. primary_email derivation
    # Rule: first emails[] entry's email, lowercased and trimmed.
    primary_email = None
    if first_email_val and str(first_email_val).strip():
        primary_email = str(first_email_val).strip().lower()

    # 3. company_name derivation
    # Rule: lead or organization display name if available on the record.
    # Looking at the OpenAPI and mapping doc, we use 'lead_name' or 'display_name'
    # provided in the source dict if present.
    company_name = source.get("lead_name") or source.get("display_name")

    # 4. custom_fields (provenance)
    # Rule: lead_id, organization_id, date_created, date_updated.
    custom_fields = {}
    for key in ["lead_id", "organization_id", "date_created", "date_updated"]:
        if (val := source.get(key)) is not None:
            custom_fields[key] = val

    return {
        "provider_id": "close",
        "external_id": source.get("id"),
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": (str(source.get("title") or "").strip()) or None,
        "company_name": (str(company_name).strip() if company_name else None) or None,
        "custom_fields": custom_fields
    }