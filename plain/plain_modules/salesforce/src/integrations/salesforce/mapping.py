from typing import Any, Dict, Optional

def map_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure transformation from Salesforce ContactRecord to conventional Contact shape.
    Following: [resource]resources/salesforce/contact-mapping.md
    """
    
    # 1. external_id
    external_id = record.get("Id")
    
    # 2. full_name derivation
    full_name = ""
    sf_name = record.get("Name")
    if sf_name and isinstance(sf_name, str):
        full_name = sf_name.strip()
    else:
        first_name = record.get("FirstName") or ""
        last_name = record.get("LastName") or ""
        full_name = f"{first_name} {last_name}".strip()
    
    # 3. primary_email
    primary_email = record.get("Email")
    if primary_email:
        primary_email = primary_email.strip().lower()
    else:
        primary_email = None
        
    # 4. job_title
    job_title = record.get("Title")
    if not job_title or job_title == "":
        job_title = None
        
    # 5. company_name (Account.Name)
    company_name = None
    account = record.get("Account")
    if isinstance(account, dict):
        acc_name = account.get("Name")
        if acc_name and acc_name != "":
            company_name = acc_name

    # 6. custom_fields
    # Consumed: Id, Name, FirstName, LastName, Email, Title, Account, attributes
    consumed_keys = {"Id", "Name", "FirstName", "LastName", "Email", "Title", "Account", "attributes"}
    custom_fields = {
        k: v for k, v in record.items() 
        if k not in consumed_keys and k != "attributes"
    }

    return {
        "provider_id": "salesforce",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }