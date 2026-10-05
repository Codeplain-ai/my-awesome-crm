from typing import Any, Dict

def map_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """Pure transformation from Dynamics 365 contact to conventional contact shape.

    Follows the rules in contact-mapping.md.
    """
    # 1. external_id
    external_id = record.get("contactid")

    # 2. full_name derivation
    fullname = (record.get("fullname") or "").strip()
    if not fullname:
        first = (record.get("firstname") or "").strip()
        last = (record.get("lastname") or "").strip()
        fullname = f"{first} {last}".strip()
    
    # 3. primary_email
    email = record.get("emailaddress1")
    primary_email = email.strip().lower() if email else None

    # 4. job_title
    job_title = record.get("jobtitle") or None

    # 5. company_name (from expanded parent account)
    parent_account = record.get("parentcustomerid_account")
    company_name = None
    if isinstance(parent_account, dict):
        company_name = parent_account.get("name") or None

    # 6. custom_fields
    consumed_keys = {
        "contactid", "fullname", "firstname", "lastname", 
        "emailaddress1", "jobtitle", "parentcustomerid_account"
    }
    custom_fields = {}
    for key, value in record.items():
        if key in consumed_keys:
            continue
        if key.startswith("@odata.") or "@" in key:
            continue
        custom_fields[key] = value

    return {
        "provider_id": "dynamics",
        "external_id": external_id,
        "full_name": fullname,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }
