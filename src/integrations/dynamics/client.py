import os
import httpx
from typing import Any, Dict, Generator, List

class DynamicsClient:
    """Client for Dynamics 365 (Dataverse) Web API."""

    def __init__(self):
        self.endpoint = os.environ.get("DYNAMICS_ENDPOINT", "").rstrip("/")
        self.tenant_id = os.environ.get("DYNAMICS_TENANT_ID")
        self.client_id = os.environ.get("DYNAMICS_CLIENT_ID")
        self.client_secret = os.environ.get("DYNAMICS_CLIENT_SECRET")
        
        missing = []
        if not self.endpoint: missing.append("DYNAMICS_ENDPOINT")
        if not self.tenant_id: missing.append("DYNAMICS_TENANT_ID")
        if not self.client_id: missing.append("DYNAMICS_CLIENT_ID")
        if not self.client_secret: missing.append("DYNAMICS_CLIENT_SECRET")
        
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    def _get_token(self) -> str:
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        scope = f"{self.endpoint}/.default"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
        }
        response = httpx.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_contacts(self) -> Generator[List[Dict[str, Any]], None, None]:
        """Fetches contacts using OData pagination."""
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        
        params = {
            "$select": "contactid,fullname,firstname,lastname,emailaddress1,jobtitle",
            "$expand": "parentcustomerid_account($select=name)",
        }
        
        url = f"{self.endpoint}/api/data/v9.2/contacts"
        
        while url:
            response = httpx.get(url, headers=headers, params=params if "?" not in url else None)
            response.raise_for_status()
            data = response.json()
            yield data.get("value", [])
            url = data.get("@odata.nextLink")
