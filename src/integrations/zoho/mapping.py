from typing import Any, Dict

def map_zoho_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements :ZohoContactMapping: logic based on contact-mapping.md.
    Maps a Zoho ContactRecord to a host-conventional Contact shape.
    """
    # 1. external_id
    external_id = record.get("id")

    # 2. full_name derivation
    full_name = ""
    # Rule 1: Full_Name field
    fn_field = record.get("Full_Name")
    if fn_field is not None and str(fn_field).strip():
        full_name = str(fn_field).strip()
    else:
        # Rule 2: First_Name + Last_Name
        first = record.get("First_Name") or ""
        last = record.get("Last_Name") or ""
        joined = f"{first} {last}".strip()
        if joined:
            full_name = joined
        else:
            # Rule 3: Email fallback
            email_val = record.get("Email")
            if email_val is not None and str(email_val).strip():
                full_name = str(email_val).strip()
            # Rule 4: Empty string (default)

    # 3. primary_email
    email_val = record.get("Email")
    primary_email = str(email_val).strip().lower() if email_val and str(email_val).strip() else None

    # 4. job_title
    title_val = record.get("Title")
    job_title = str(title_val).strip() if title_val and str(title_val).strip() else None

    # 5. company_name derivation
    account_name = record.get("Account_Name")
    company_name = None
    if isinstance(account_name, dict):
        # Rule 1: Object shape
        val = account_name.get("name")
        if val is not None and str(val).strip():
            company_name = str(val).strip()
    elif isinstance(account_name, str):
        # Rule 2: String shape
        if account_name.strip():
            company_name = account_name.strip()
    # Rule 3: null/missing maps to None

    # 6. custom_fields rules
    consumed_keys = {"id", "Full_Name", "First_Name", "Last_Name", "Email", "Title", "Account_Name"}
    custom_fields = {}
    for k, v in record.items():
        if k in consumed_keys:
            continue
        # Exclude Zoho system metadata starting with $
        if k.startswith("$"):
            continue
        # Exclude Owner lookup object
        if k == "Owner":
            continue
        custom_fields[k] = v

    return {
        "provider_id": "zoho",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }