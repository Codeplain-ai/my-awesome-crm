import httpx
from typing import Any, Generator

class SalesforceClient:
    """
    Minimal Salesforce REST API client focused on Contact retrieval.
    """
    def __init__(self, endpoint: str, client_id: str, client_secret: str):
        self.endpoint = endpoint.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._instance_url = None

    def _authenticate(self):
        """Acquires a bearer token using client_credentials flow."""
        token_url = f"{self.endpoint}/services/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            response = httpx.post(token_url, data=data, timeout=10.0)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Salesforce authentication failed ({response.status_code}): {response.text}"
                )
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to connect to Salesforce for authentication: {str(e)}")
            
        payload = response.json()
        self._access_token = payload["access_token"]
        self._instance_url = payload["instance_url"].rstrip("/")

    def get_all_contacts(self) -> Generator[dict[str, Any], None, None]:
        """Queries Salesforce for contacts, handling pagination."""
        if not self._access_token:
            self._authenticate()

        # Initial query
        soql = "SELECT Id, Name, FirstName, LastName, Email, Title, Account.Name FROM Contact"
        url = f"{self._instance_url}/services/data/v60.0/query/"
        params = {"q": soql}
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json"
        }

        while url:
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Salesforce query failed ({response.status_code}): {response.text}"
                    )
                
                data = response.json()
                for record in data.get("records", []):
                    yield record

                # Handle pagination: nextRecordsUrl is a relative path
                next_path = data.get("nextRecordsUrl")
                if next_path and not data.get("done", True):
                    url = f"{self._instance_url}{next_path}"
                    params = None  # SOQL query 'q' is not sent on subsequent pages
                else:
                    url = None
            except httpx.RequestError as e:
                raise RuntimeError(f"Network error during Salesforce query: {str(e)}")