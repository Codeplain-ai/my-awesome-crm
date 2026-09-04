import httpx
from typing import Any, Dict, Generator, List, Optional

class DynamicsClient:
    """
    Client for Dynamics 365 / Dataverse API using httpx.
    Follows the surface defined in resources/dynamics/openapi.yaml.
    """
    def __init__(self, client_id: str, client_secret: str, tenant_id: str, endpoint: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.endpoint = endpoint
        self.access_token: Optional[str] = None

    def _get_token(self) -> str:
        """Azure AD OAuth 2.0 client-credentials token request."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": f"{self.endpoint}/.default"
        }
        response = httpx.post(url, data=data, timeout=30.0)
        if response.status_code != 200:
            raise RuntimeError(f"Auth failed: {response.status_code} {response.text}")
        return response.json()["access_token"]

    def list_contacts(self) -> Generator[List[Dict[str, Any]], None, None]:
        """Queries contacts with pagination support."""
        if not self.access_token:
            self.access_token = self._get_token()

        # OData projection and expansion as per resources/dynamics/openapi.yaml
        params = {
            "$select": "contactid,fullname,firstname,lastname,emailaddress1,jobtitle",
            "$expand": "parentcustomerid_account($select=name)"
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        url = f"{self.endpoint}/api/data/v9.2/contacts"
        
        is_first_page = True
        while url:
            # Note: @odata.nextLink is an absolute URL. Params are only used on the first call.
            response = httpx.get(
                url, 
                params=params if is_first_page else None, 
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            is_first_page = False
            
            data = response.json()
            yield data.get("value", [])
            
            # Stop when @odata.nextLink is absent
            url = data.get("@odata.nextLink")