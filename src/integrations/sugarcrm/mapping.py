import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def map_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure transformation from SugarCRM ContactRecord to host Contact shape.
    Strictly follows [resource]resources/sugarcrm/contact-mapping.md.
    """
    # 1. Primary Email Selection
    primary_email = _select_primary_email(record)

    # 2. Full Name Derivation
    full_name = _derive_full_name(record, primary_email)

    # 3. Custom Fields (provenance only)
    custom_fields = {}
    if record.get("date_entered"):
        custom_fields["date_entered"] = record["date_entered"]
    if record.get("date_modified"):
        custom_fields["date_modified"] = record["date_modified"]

    # 4. Construct Output
    return {
        "provider_id": "sugarcrm",
        "external_id": record.get("id"),
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": record.get("title") or None,
        "company_name": record.get("account_name") or None,
        "custom_fields": custom_fields
    }

def _select_primary_email(record: Dict[str, Any]) -> Optional[str]:
    """Logic for primary_email selection rules."""
    email_list: List[Dict[str, Any]] = record.get("email") or []
    selected = None

    # Try structured email array
    for entry in email_list:
        if entry.get("primary_address"):
            selected = entry.get("email_address")
            break
    
    if not selected:
        for entry in email_list:
            addr = entry.get("email_address")
            if addr:
                selected = addr
                break
    
    # Fallback to flat field email1
    if not selected:
        selected = record.get("email1")

    if selected:
        return selected.strip().lower()
    return None

def _derive_full_name(record: Dict[str, Any], selected_email: Optional[str]) -> str:
    """Logic for full_name derivation rules."""
    # 1. Check full_name or name
    fn = record.get("full_name")
    if fn and fn.strip():
        return fn.strip()
    
    n = record.get("name")
    if n and n.strip():
        return n.strip()
    
    # 2. Join first/last
    first = record.get("first_name") or ""
    last = record.get("last_name") or ""
    joined = f"{first} {last}".strip()
    if joined:
        return joined
    
    # 3. Email fallback
    if selected_email:
        return selected_email.strip()
    
    # 4. Empty string
    return ""