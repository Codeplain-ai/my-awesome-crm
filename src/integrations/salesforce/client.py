import os
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

class SalesforceClient:
    """
    Client for Salesforce REST API v60.0.
    Handles authentication and paginated queries.
    """
    def __init__(self):
        self.endpoint = self._get_env_required("SALESFORCE_ENDPOINT")
        self.client_id = self._get_env_required("SALESFORCE_CLIENT_ID")
        self.client_secret = self._get_env_required("SALESFORCE_CLIENT_SECRET")
        self.access_token: Optional[str] = None
        self.instance_url: Optional[str] = None

    def _get_env_required(self, key: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing environment variable: {key}")
        return val

    def authenticate(self):
        """Acquires bearer token via client_credentials flow."""
        url = f"{self.endpoint.rstrip('/')}/services/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            response = httpx.post(url, data=data, timeout=30.0)
            response.raise_for_status()
            res_data = response.json()
            self.access_token = res_data["access_token"]
            self.instance_url = res_data["instance_url"].rstrip('/')
        except httpx.HTTPError as e:
            logger.error(f"Salesforce authentication failed: {str(e)}")
            raise RuntimeError(f"Salesforce authentication failed: {str(e)}")

    def query_all_contacts(self) -> list[dict[str, Any]]:
        """Fetches all contacts using the pinned SOQL query, handling pagination."""
        if not self.access_token or not self.instance_url:
            self.authenticate()

        soql = "SELECT Id, Name, FirstName, LastName, Email, Title, Account.Name FROM Contact"
        query_path = "/services/data/v60.0/query/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        
        all_records = []
        current_url = f"{self.instance_url}{query_path}"
        params: Optional[dict[str, str]] = {"q": soql}

        try:
            while current_url:
                response = httpx.get(
                    current_url, 
                    params=params, 
                    headers=headers, 
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                all_records.extend(data.get("records", []))
                
                next_page = data.get("nextRecordsUrl")
                if not data.get("done", True) and next_page:
                    # nextRecordsUrl is the full relative path, e.g. /services/data/...
                    current_url = f"{self.instance_url}{next_page}"
                    params = None # Parameters are already encoded in the nextRecordsUrl
                else:
                    current_url = None
        except httpx.HTTPError as e:
            logger.error(f"Salesforce query failed: {str(e)}")
            raise RuntimeError(f"Salesforce query failed: {str(e)}")

        return all_records