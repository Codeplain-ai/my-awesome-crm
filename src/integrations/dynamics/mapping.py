from typing import Any, Dict, Optional

def map_contact(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure function implementing DynamicsContactMapping.
    Maps a raw Dataverse contact record to the host's Contact shape.
    """
    # 1. full_name derivation
    fullname = (source.get("fullname") or "").strip()
    if not fullname:
        fname = (source.get("firstname") or "").strip()
        lname = (source.get("lastname") or "").strip()
        fullname = f"{fname} {lname}".strip()
    
    # 2. primary_email
    email = source.get("emailaddress1")
    primary_email = email.lower().strip() if email else None
    
    # 3. company_name (from expanded parentcustomerid_account)
    parent_account = source.get("parentcustomerid_account")
    company_name = None
    if isinstance(parent_account, dict):
        company_name = parent_account.get("name") or None

    # 4. custom_fields (Exclude consumed fields and OData metadata)
    consumed = {
        "contactid", "fullname", "firstname", "lastname",
        "emailaddress1",
        "jobtitle", "parentcustomerid_account"
    }
    
    custom_fields = {}
    for key, value in source.items():
        if key in consumed:
            continue
        if "@odata." in key or "@" in key:
            continue
        custom_fields[key] = value

    return {
        "provider_id": "dynamics",
        "external_id": source.get("contactid"),
        "full_name": fullname,
        "primary_email": primary_email,
        "job_title": source.get("jobtitle") or None,
        "company_name": company_name,
        "custom_fields": custom_fields
    }