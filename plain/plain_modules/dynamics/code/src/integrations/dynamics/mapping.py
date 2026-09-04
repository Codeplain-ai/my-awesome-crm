from typing import Any, Dict

def map_contact_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implementation of :DynamicsContactMapping:.
    Maps a Dataverse ContactRecord to a host :Contact: data dict.
    """
    # 1. external_id: contactid GUID
    external_id = record.get("contactid")

    # 2. full_name derivation rules
    fullname_val = record.get("fullname")
    if fullname_val and fullname_val.strip():
        full_name = fullname_val.strip()
    else:
        first = record.get("firstname") or ""
        last = record.get("lastname") or ""
        full_name = f"{first} {last}".strip()

    # 3. primary_email: emailaddress1 lowercased and trimmed
    email_val = record.get("emailaddress1")
    primary_email = email_val.strip().lower() if email_val and email_val.strip() else None

    # 4. job_title
    job_val = record.get("jobtitle")
    job_title = job_val if job_val and job_val.strip() else None

    # 5. company_name: from expanded parentcustomerid_account
    company_name = None
    parent_account = record.get("parentcustomerid_account")
    if isinstance(parent_account, dict):
        acc_name = parent_account.get("name")
        if acc_name and acc_name.strip():
            company_name = acc_name

    # 6. custom_fields: capture all non-consumed, non-metadata fields
    consumed_keys = {
        "contactid", "fullname", "firstname", "lastname", 
        "emailaddress1", "jobtitle", "parentcustomerid_account"
    }
    custom_fields = {}
    for key, value in record.items():
        if key in consumed_keys:
            continue
        # Rule: Skip API metadata (@odata.*) and OData annotations (containing @)
        if key.startswith("@odata.") or "@" in key:
            continue
        custom_fields[key] = value

    return {
        "provider_id": "dynamics",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }