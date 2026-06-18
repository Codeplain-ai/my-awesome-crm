import logging
from typing import Any, Dict, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def map_zoho_contact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements :ZohoContactMapping: as a pure function.
    Converts a Zoho Contact record into an IncomingContact dict.
    
    Raises ValueError for missing external_id or missing full_name.
    """
    # 1. external_id (id) - Required
    external_id = record.get("id")
    if not external_id or not str(external_id).strip():
        raise ValueError("Zoho record is missing required 'id' field.")
    
    # 2. primary_email validation
    raw_email = record.get("Email")
    primary_email: Optional[str] = None
    if raw_email and str(raw_email).strip():
        email_candidate = str(raw_email).strip()
        try:
            # Match host's check: check_deliverability=False
            valid = validate_email(email_candidate, check_deliverability=False)
            primary_email = valid.normalized.lower()
        except EmailNotValidError:
            logger.warning(
                f"Contact {external_id} has invalid email address: {email_candidate}"
            )
            primary_email = None

    # 3. full_name derivation
    full_name: Optional[str] = None
    
    # Rule 1: Full_Name
    fn_field = record.get("Full_Name")
    if fn_field and str(fn_field).strip():
        full_name = str(fn_field).strip()
    
    # Rule 2: First_Name + Last_Name
    if not full_name:
        first = (record.get("First_Name") or "").strip()
        last = (record.get("Last_Name") or "").strip()
        joined = f"{first} {last}".strip()
        if joined:
            full_name = joined
            
    # Rule 3: Email
    if not full_name:
        if raw_email and str(raw_email).strip():
            full_name = str(raw_email).strip()
            
    if not full_name:
        raise ValueError(f"Contact {external_id} has no derivable full_name.")

    # 4. phone derivation (Phone else Mobile)
    phone = record.get("Phone")
    if not phone or not str(phone).strip():
        phone = record.get("Mobile")
    
    phone_val = str(phone).strip() if phone and str(phone).strip() else None

    # 5. job_title (Title)
    title = record.get("Title")
    job_title = str(title).strip() if title and str(title).strip() else None

    # 6. company_name (Account_Name derivation)
    account_name = record.get("Account_Name")
    company_name: Optional[str] = None
    
    if isinstance(account_name, dict):
        # Case 1: Object lookup
        name_val = account_name.get("name")
        if name_val and str(name_val).strip():
            company_name = str(name_val).strip()
    elif isinstance(account_name, str):
        # Case 2: Plain string
        if account_name.strip():
            company_name = account_name.strip()
    # Case 3: null/missing -> None (already initialized)

    # 7. custom_fields
    consumed_keys = {
        "id", "Full_Name", "First_Name", "Last_Name", 
        "Email", "Phone", "Mobile", "Title", "Account_Name"
    }
    custom_fields = {}
    for key, value in record.items():
        if key in consumed_keys:
            continue
        if key.startswith("$"):
            continue
        if key == "Owner":
            continue
        custom_fields[key] = value

    return {
        "provider_id": "zoho",
        "external_id": str(external_id),
        "full_name": full_name,
        "primary_email": primary_email,
        "phone": phone_val,
        "job_title": job_title,
        "company_name": company_name,
        "custom_fields": custom_fields
    }