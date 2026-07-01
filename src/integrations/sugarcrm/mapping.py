import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def map_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements :SugarCrmContactMapping: for a single SugarCRM Contact record.
    Ref: [resource]resources/sugarcrm/contact-mapping.md
    """
    # 1. Primary Email Selection
    email_val = None
    email_list = raw.get("email")
    if isinstance(email_list, list) and len(email_list) > 0:
        # Find primary_address entry
        primary_entry = next(
            (e for e in email_list if e.get("primary_address") is True or str(e.get("primary_address")).lower() == "true"),
            None
        )
        if primary_entry:
            email_val = primary_entry.get("email_address")
        
        # Fallback to first non-empty email_address if no primary
        if not email_val:
            email_val = next(
                (e.get("email_address") for e in email_list if e.get("email_address")),
                None
            )

    # Fallback to flat email1 field
    if not email_val:
        email_val = raw.get("email1")

    # Canonicalize email
    primary_email = None
    if email_val and isinstance(email_val, str):
        stripped_email = email_val.strip()
        if stripped_email:
            primary_email = stripped_email.lower()

    # 2. full_name Derivation
    full_name = ""
    # Rule 1: full_name or name
    fn_field = raw.get("full_name")
    n_field = raw.get("name")
    if fn_field and str(fn_field).strip():
        full_name = str(fn_field).strip()
    elif n_field and str(n_field).strip():
        full_name = str(n_field).strip()
    else:
        # Rule 2: first + last
        first = str(raw.get("first_name") or "").strip()
        last = str(raw.get("last_name") or "").strip()
        joined = f"{first} {last}".strip()
        if joined:
            full_name = joined
        elif primary_email:
            # Rule 3: primary_email trimmed
            full_name = email_val.strip() if email_val else ""

    # 3. Custom Fields
    # Rule: capture provenance timestamps, exclude business keys and API metadata (_)
    business_keys = {
        "id", "first_name", "last_name", "name", "full_name",
        "email", "email1",
        "title", "account_name"
    }
    custom_fields = {}
    for k, v in raw.items():
        if k in ("date_entered", "date_modified") and v is not None:
            custom_fields[k] = v
        elif k not in business_keys and not k.startswith("_"):
            # Per contract: only date_entered/date_modified are explicitly listed 
            # for inclusion, but we follow the exclusion rules for safety.
            pass

    return {
        "provider_id": "sugarcrm",
        "external_id": raw.get("id"),
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": raw.get("title") or None,
        "company_name": raw.get("account_name") or None,
        "custom_fields": custom_fields,
    }