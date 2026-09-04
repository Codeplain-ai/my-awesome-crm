from typing import Any, Dict, List, Optional

def map_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a Streak ContactRecord to the conventional Contact shape.
    Follows [resource]resources/streak/contact-mapping.md.
    """
    # external_id mapping
    external_id = record.get("key")

    # full_name derivation
    full_name = _derive_full_name(record)

    # primary_email derivation
    emails = record.get("emailAddresses", [])
    primary_email = None
    if isinstance(emails, list) and len(emails) > 0:
        first_email = emails[0]
        if first_email:
            primary_email = str(first_email).strip().lower()

    # job_title
    job_title = record.get("title")
    if not job_title: # handles empty string or None
        job_title = None

    # custom_fields
    custom_fields = {}
    if "creationTimestamp" in record and record["creationTimestamp"] is not None:
        custom_fields["creationTimestamp"] = record["creationTimestamp"]
    if "lastSavedTimestamp" in record and record["lastSavedTimestamp"] is not None:
        custom_fields["lastSavedTimestamp"] = record["lastSavedTimestamp"]

    return {
        "provider_id": "streak",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": None,
        "custom_fields": custom_fields
    }

def _derive_full_name(record: Dict[str, Any]) -> str:
    # 1. fullName
    fn = record.get("fullName")
    if fn and str(fn).strip():
        return str(fn).strip()
    
    # 2. givenName + familyName
    gn = record.get("givenName") or ""
    fam = record.get("familyName") or ""
    joined = f"{gn} {fam}".strip()
    if joined:
        return joined
    
    # 3. First email address
    emails = record.get("emailAddresses", [])
    if isinstance(emails, list) and len(emails) > 0:
        first_email = emails[0]
        if first_email and str(first_email).strip():
            return str(first_email).strip()
            
    # 4. Fallback
    return ""