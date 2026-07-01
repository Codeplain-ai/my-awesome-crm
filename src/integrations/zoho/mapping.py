from typing import Any


def map_contact(raw_record: dict[str, Any]) -> dict[str, Any]:
    """
    Maps a Zoho CRM Contact record to a standard Contact data dict.
    Follows the contract in resources/zoho/contact-mapping.md.
    """
    full_name = _derive_full_name(raw_record)
    primary_email = _derive_primary_email(raw_record)
    company_name = _derive_company_name(raw_record)
    
    # job_title: Title value, or None when missing or empty.
    job_title = raw_record.get("Title") or None
    if job_title:
        job_title = job_title.strip() or None

    return {
        "provider_id": "zoho",
        "external_id": raw_record.get("id"),
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": _extract_custom_fields(raw_record),
    }


def _derive_full_name(raw: dict[str, Any]) -> str:
    """
    Derivation rules:
    1. Full_Name (stripped)
    2. First_Name + Last_Name (joined, stripped)
    3. Email (trimmed)
    4. Empty string
    """
    # 1. Full_Name
    val = raw.get("Full_Name")
    if val and isinstance(val, str) and val.strip():
        return val.strip()

    # 2. First_Name + Last_Name
    first = (raw.get("First_Name") or "").strip()
    last = (raw.get("Last_Name") or "").strip()
    joined = f"{first} {last}".strip()
    if joined:
        return joined

    # 3. Email
    email = raw.get("Email")
    if email and isinstance(email, str) and email.strip():
        return email.strip()

    # 4. Fallback
    return ""


def _derive_primary_email(raw: dict[str, Any]) -> str | None:
    """Email lowercased and trimmed, or None."""
    val = raw.get("Email")
    if val and isinstance(val, str) and val.strip():
        return val.strip().lower()
    return None


def _derive_company_name(raw: dict[str, Any]) -> str | None:
    """
    Account_Name lookup rules:
    1. Object: use name field
    2. String: use string directly
    3. Null/Missing: None
    """
    val = raw.get("Account_Name")
    if not val:
        return None

    if isinstance(val, dict):
        name = val.get("name")
        if name and isinstance(name, str) and name.strip():
            return name.strip()
        return None

    if isinstance(val, str):
        return val.strip() or None

    return None


def _extract_custom_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Captures all fields except consumed ones and Zoho system metadata.
    System metadata starts with '$' or is the 'Owner' lookup.
    """
    consumed_keys = {
        "id",
        "Full_Name",
        "First_Name",
        "Last_Name",
        "Email",
        "Title",
        "Account_Name",
    }
    custom = {}
    for key, value in raw.items():
        if key in consumed_keys:
            continue
        if key.startswith("$"):
            continue
        if key == "Owner":
            continue
        custom[key] = value
    return custom