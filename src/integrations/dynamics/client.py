import os
import logging
import requests
from typing import Any
from .mapping import dynamics_contact_to_incoming

logger = logging.getLogger(__name__)

def _get_credentials() -> dict[str, str]:
    keys = [
        "DYNAMICS_TENANT_ID",
        "DYNAMICS_CLIENT_ID",
        "DYNAMICS_CLIENT_SECRET",
        "DYNAMICS_RESOURCE_URL"
    ]
    creds = {}
    for key in keys:
        val = os.getenv(key)
        if not val:
            raise RuntimeError(f"Missing required environment variable: {key}")
        creds[key] = val
    return creds

def _acquire_token(creds: dict[str, str]) -> str:
    tenant_id = creds["DYNAMICS_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": creds["DYNAMICS_CLIENT_ID"],
        "client_secret": creds["DYNAMICS_CLIENT_SECRET"],
        "scope": f"{creds['DYNAMICS_RESOURCE_URL']}/.default"
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def _get_json(url: str, token: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def fetch_contacts() -> list[dict[str, Any]]:
    creds = _get_credentials()
    token = _acquire_token(creds)
    
    base_url = creds["DYNAMICS_RESOURCE_URL"].rstrip("/")
    select = "contactid,fullname,firstname,lastname,emailaddress1,telephone1,mobilephone,jobtitle,department"
    expand = "parentcustomerid_account($select=name)"
    next_url = f"{base_url}/api/data/v9.2/contacts?$select={select}&$expand={expand}"
    
    all_contacts = []
    
    while next_url:
        data = _get_json(next_url, token)
        records = data.get("value", [])
        
        for record in records:
            try:
                incoming = dynamics_contact_to_incoming(record)
                all_contacts.append(incoming)
            except ValueError as e:
                contact_id = record.get("contactid", "unknown")
                logger.warning("Skipping malformed Dynamics contact %s: %s", contact_id, e)
        
        next_url = data.get("@odata.nextLink")
        
    return all_contacts