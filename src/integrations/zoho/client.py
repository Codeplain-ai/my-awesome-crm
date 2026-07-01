import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

class ZohoClient:
    """
    Client for Zoho CRM v3 REST API.
    Grounded in resources/zoho/openapi.yaml.
    """
    def __init__(
        self,
        accounts_host: str,
        api_host: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        self.accounts_host = accounts_host.rstrip("/")
        self.api_host = api_host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: Optional[str] = None

    def _get_access_token(self) -> str:
        """Acquires a fresh access token via refresh-token grant."""
        url = f"{self.accounts_host}/oauth/v2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        
        response = httpx.post(url, data=data)
        if response.status_code != 200:
            logger.error(
                f"Zoho token refresh failed: {response.status_code}",
                extra={"body": response.text}
            )
            raise RuntimeError(f"Failed to refresh Zoho token: {response.text}")
            
        token_data = response.json()
        if "access_token" not in token_data:
            raise RuntimeError(f"Zoho token response missing access_token: {token_data}")
            
        return token_data["access_token"]

    def fetch_contacts_page(self, page: int = 1) -> tuple[List[Dict[str, Any]], bool]:
        """
        Fetches one page of contacts.
        Returns (list of records, has_more_records).
        """
        if not self.access_token:
            self.access_token = self._get_access_token()

        url = f"{self.api_host}/crm/v3/Contacts"
        params = {
            "fields": "id,Full_Name,First_Name,Last_Name,Email,Title,Account_Name",
            "per_page": 200,
            "page": page,
        }
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}

        response = httpx.get(url, params=params, headers=headers)

        if response.status_code == 204:
            return [], False
            
        if response.status_code != 200:
            logger.error(
                f"Zoho listContacts failed: {response.status_code}",
                extra={"body": response.text}
            )
            raise RuntimeError(f"Failed to fetch Zoho contacts: {response.text}")

        payload = response.json()
        records = payload.get("data", [])
        info = payload.get("info", {})
        has_more = info.get("more_records", False)

        return records, has_more

    def fetch_all_contacts(self) -> List[Dict[str, Any]]:
        """Iterates through all pages of contacts."""
        all_records = []
        page = 1
        has_more = True
        
        while has_more:
            records, has_more = self.fetch_contacts_page(page)
            all_records.extend(records)
            page += 1
            
        return all_records