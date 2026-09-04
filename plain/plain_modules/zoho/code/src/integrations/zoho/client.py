import os
import httpx
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class ZohoClient:
    """
    Handles communication with the Zoho CRM v3 REST API.
    Follows the surface defined in [resource]resources/zoho/openapi.yaml.
    """
    def __init__(self):
        self.accounts_host = os.environ.get("ZOHO_ACCOUNTS_HOST")
        self.api_host = os.environ.get("ZOHO_API_HOST")
        self.client_id = os.environ.get("ZOHO_CLIENT_ID")
        self.client_secret = os.environ.get("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN")
        self.access_token: str | None = None

    def _validate_env(self) -> None:
        """Validates that all required environment variables are present."""
        required = {
            "ZOHO_ACCOUNTS_HOST": self.accounts_host,
            "ZOHO_API_HOST": self.api_host,
            "ZOHO_CLIENT_ID": self.client_id,
            "ZOHO_CLIENT_SECRET": self.client_secret,
            "ZOHO_REFRESH_TOKEN": self.refresh_token,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    def authenticate(self) -> None:
        """
        Mints a fresh access token using the refresh_token grant.
        Endpoint: POST {ZOHO_ACCOUNTS_HOST}/oauth/v2/token
        """
        self._validate_env()

        # accounts_host is validated non-empty by _validate_env
        url = f"{self.accounts_host.rstrip('/')}/oauth/v2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        
        try:
            response = httpx.post(url, data=data, timeout=30.0)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Zoho auth failed with status {response.status_code}: {response.text}"
                )
            
            token_data = response.json()
            if "access_token" not in token_data:
                raise RuntimeError(f"Zoho auth response missing 'access_token': {token_data}")
                
            self.access_token = token_data["access_token"]
            logger.info("Successfully authenticated with Zoho CRM")
            
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to connect to Zoho Accounts: {str(e)}") from e

    def list_contacts(self) -> List[Dict[str, Any]]:
        """
        Fetches all contacts from Zoho using the Contacts module API.
        Handles pagination until no more records are available.
        Endpoint: GET {ZOHO_API_HOST}/crm/v3/Contacts
        """
        if not self.access_token:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        contacts = []
        page = 1
        more_records = True
        
        while more_records:
            # api_host is validated non-empty by _validate_env
            url = f"{self.api_host.rstrip('/')}/crm/v3/Contacts"
            params = {
                "fields": "id,Full_Name,First_Name,Last_Name,Email,Title,Account_Name",
                "per_page": 200,
                "page": page
            }
            headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
            
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=60.0)
                
                # Zoho returns 204 No Content when no records exist or no further page
                if response.status_code == 204:
                    logger.debug(f"Zoho returned 204 No Content for page {page}")
                    break
                
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Zoho API error for page {page} (Status {response.status_code}): {response.text}"
                    )
                
                data = response.json()
                page_data = data.get("data", [])
                if not page_data:
                    break
                    
                contacts.extend(page_data)
                
                info = data.get("info", {})
                more_records = info.get("more_records", False)
                page += 1
                
            except httpx.RequestError as e:
                raise RuntimeError(f"Failed to connect to Zoho API: {str(e)}") from e
            
        logger.info(f"Fetched {len(contacts)} contacts from Zoho CRM")
        return contacts