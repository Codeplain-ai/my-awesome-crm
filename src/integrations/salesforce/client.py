import os
import httpx
from typing import Any, Dict, List, Optional

class SalesforceClient:
    """
    Client for Salesforce REST API surface.
    Handles authentication and paginated queries.
    """
    def __init__(self):
        self.client_id = os.environ.get("SALESFORCE_CLIENT_ID")
        self.client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")
        self.endpoint = os.environ.get("SALESFORCE_ENDPOINT")  # Login host

        missing = []
        if not self.client_id:
            missing.append("SALESFORCE_CLIENT_ID")
        if not self.client_secret:
            missing.append("SALESFORCE_CLIENT_SECRET")
        if not self.endpoint:
            missing.append("SALESFORCE_ENDPOINT")

        if missing:
            raise RuntimeError(f"Missing required Salesforce environment variables: {', '.join(missing)}")

    def _get_access_token(self) -> tuple[str, str]:
        """Acquires OAuth2 token using client_credentials flow."""
        url = f"{self.endpoint.rstrip('/')}/services/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        with httpx.Client() as client:
            response = client.post(url, data=data)
            if response.status_code != 200:
                raise RuntimeError(f"Salesforce auth failed: {response.text}")
            
            payload = response.json()
            return payload["access_token"], payload["instance_url"]

    def get_all_contacts(self) -> List[Dict[str, Any]]:
        """Fetches all contacts using the SOQL query defined in OpenAPI."""
        access_token, instance_url = self._get_access_token()
        
        # SOQL query pinned by OpenAPI spec
        query = "SELECT Id, Name, FirstName, LastName, Email, Title, Account.Name FROM Contact"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        records = []
        # Initial request
        url = f"{instance_url.rstrip('/')}/services/data/v60.0/query/"
        params = {"q": query}
        
        with httpx.Client(headers=headers) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Salesforce query failed: {resp.text}")
            
            data = resp.json()
            records.extend(data.get("records", []))
            
            # Multi-page pagination: follow nextRecordsUrl
            while not data.get("done", True) and "nextRecordsUrl" in data:
                next_url = f"{instance_url.rstrip('/')}{data['nextRecordsUrl']}"
                resp = client.get(next_url)
                if resp.status_code != 200:
                    raise RuntimeError(f"Salesforce pagination failed: {resp.text}")
                data = resp.json()
                records.extend(data.get("records", []))
                
        return records