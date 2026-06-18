import logging
import os
from typing import Iterable, Any
import httpx

from .mapping import map_dynamics_contact

logger = logging.getLogger(__name__)

def _get_credentials() -> dict[str, str]:
    keys = [
        "DYNAMICS_ENDPOINT",
        "DYNAMICS_TENANT_ID",
        "DYNAMICS_CLIENT_ID",
        "DYNAMICS_CLIENT_SECRET",
    ]
    creds = {}
    for key in keys:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing required environment variable: {key}")
        creds[key] = val
    return creds

def _get_access_token(creds: dict[str, str]) -> str:
    tenant_id = creds["DYNAMICS_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    scope = creds["DYNAMICS_ENDPOINT"].rstrip("/") + "/.default"
    data = {
        "grant_type": "client_credentials",
        "client_id": creds["DYNAMICS_CLIENT_ID"],
        "client_secret": creds["DYNAMICS_CLIENT_SECRET"],
        "scope": scope,
    }
    
    response = httpx.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Main entry point for the Dynamics 365 integration.
    """
    creds = _get_credentials()
    token = _get_access_token(creds)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
    }
    
    # Construct initial URL with required OData params
    # Field list and expansion per openapi.yaml
    select_fields = "contactid,fullname,firstname,lastname,emailaddress1,telephone1,mobilephone,jobtitle"
    expand_clause = "parentcustomerid_account($select=name)"
    
    next_link = (
        f"{creds['DYNAMICS_ENDPOINT'].rstrip('/')}/api/data/v9.2/contacts"
        f"?$select={select_fields}&$expand={expand_clause}"
    )

    with httpx.Client(headers=headers) as client:
        while next_link:
            logger.info(f"Fetching Dynamics contacts from: {next_link}")
            response = client.get(next_link)
            response.raise_for_status()
            
            page_data = response.json()
            records = page_data.get("value", [])
            
            for raw_record in records:
                try:
                    yield map_dynamics_contact(raw_record)
                except ValueError as ve:
                    # Skip-and-log policy
                    contact_id = raw_record.get("contactid", "unknown")
                    logger.warning(
                        f"Skipping malformed Dynamics record {contact_id}: {str(ve)}"
                    )
            
            next_link = page_data.get("@odata.nextLink")

__all__ = ["fetch_contacts"]