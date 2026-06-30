from typing import Any, Callable, List

# Integration metadata
DATA_TYPE = "contact"

import os
import httpx
from src.integrations.salesforce.mapping import map_contact

__all__ = ["DATA_TYPE", "fetch"]

def _get_credentials() -> tuple[str, str, str]:
    """Reads credentials from environment or raises RuntimeError."""
    keys = ["SALESFORCE_ENDPOINT", "SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"]
    values = []
    for key in keys:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(key)
        values.append(val)
    return values[0], values[1], values[2]

def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Fetches contacts from Salesforce using the REST API.
    """
    endpoint, client_id, client_secret = _get_credentials()

    with httpx.Client(timeout=30.0) as client:
        # 1. Acquire Token
        token_url = f"{endpoint.rstrip('/')}/services/oauth2/token"
        token_resp = client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if token_resp.status_code != 200:
            raise RuntimeError(f"Salesforce auth failed: {token_resp.text}")
        
        auth_data = token_resp.json()
        access_token = auth_data["access_token"]
        instance_url = auth_data["instance_url"].rstrip("/")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        # 2. Query Loop (Pagination)
        records = []
        # Initial query
        query = "SELECT Id, Name, FirstName, LastName, Email, Phone, MobilePhone, Title, Account.Name FROM Contact"
        next_url = f"{instance_url}/services/data/v60.0/query/?q={query}"

        while next_url:
            resp = client.get(next_url, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Salesforce query failed: {resp.text}")
            
            page_data = resp.json()
            records.extend(page_data.get("records", []))

            if not page_data.get("done", True) and "nextRecordsUrl" in page_data:
                # nextRecordsUrl is a relative path like /services/data/v60.0/query/01g...
                next_url = f"{instance_url}{page_data['nextRecordsUrl']}"
            else:
                next_url = None

        # 3. Map records
        return [map_contact(r) for r in records]