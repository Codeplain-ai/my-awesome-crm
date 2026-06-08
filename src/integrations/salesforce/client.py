import os
import logging
import requests
from typing import Iterable, Any
from .mapping import salesforce_contact_to_incoming

logger = logging.getLogger(__name__)

def _get_credentials() -> dict[str, str]:
    creds = {
        "endpoint": os.environ.get("SALESFORCE_ENDPOINT", ""),
        "client_id": os.environ.get("SALESFORCE_CLIENT_ID", ""),
        "client_secret": os.environ.get("SALESFORCE_CLIENT_SECRET", ""),
    }
    if not all(creds.values()):
        missing = [k for k, v in creds.items() if not v]
        raise RuntimeError(f"Missing Salesforce credentials: {', '.join(missing)}")
    return creds

def _acquire_token(creds: dict[str, str]) -> tuple[str, str]:
    """
    Acquires an OAuth2 bearer token and instance URL.
    """
    token_url = f"{creds['endpoint'].rstrip('/')}/services/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
    }
    response = requests.post(token_url, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["access_token"], data["instance_url"]

def _get_json(url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Performs an authenticated GET request and returns parsed JSON.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json()

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Orchestrates the Salesforce contact pull and returns a list of mapped contacts.
    """
    creds = _get_credentials()
    token, instance_url = _acquire_token(creds)
    instance_url = instance_url.rstrip("/")

    soql = "SELECT Id, Name, FirstName, LastName, Email, Phone, MobilePhone, Title, Account.Name FROM Contact"
    query_path = "/services/data/v60.0/query/"
    
    current_url = f"{instance_url}{query_path}"
    params: dict[str, Any] | None = {"q": soql}
    
    results: list[dict[str, Any]] = []

    while current_url:
        page_data = _get_json(current_url, token, params)
        params = None  # Params only used for the initial query call

        for record in page_data.get("records", []):
            try:
                mapped = salesforce_contact_to_incoming(record)
                results.append(mapped)
            except ValueError as e:
                contact_id = record.get("Id", "unknown")
                logger.warning(
                    "Skipping malformed Salesforce contact %s: %s", 
                    contact_id, e, extra={"record": record}
                )

        if page_data.get("done") is True:
            current_url = ""
        else:
            next_path = page_data.get("nextRecordsUrl")
            current_url = f"{instance_url}{next_path}" if next_path else ""

    return results