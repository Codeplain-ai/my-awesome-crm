import logging
from typing import Generator, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class ZendeskSellClient:
    """
    HTTP Client for Zendesk Sell v2 API.
    Handles authentication, mandatory headers, and pagination following meta.links.next_page.
    """
    BASE_URL = "https://api.getbase.com"
    USER_AGENT = "CRM-Integration-Host/1.0 (Zendesk Sell Integration)"

    def __init__(self, token: str):
        if not token:
            raise ValueError("Zendesk Sell access token cannot be empty")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT
        }

    def list_all_contacts(self) -> Generator[Dict[str, Any], None, None]:
        """
        Yields every contact from the /v2/contacts endpoint by following pagination links.
        """
        url = f"{self.BASE_URL}/v2/contacts"
        params: Optional[Dict[str, Any]] = {"per_page": 100}

        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            while url:
                logger.debug(f"Fetching Zendesk Sell contacts from: {url}")
                # After the first page, the URL from next_page is used verbatim (params=None)
                response = client.get(url, params=params)
                
                if response.status_code == 401:
                    raise RuntimeError(
                        f"Zendesk Sell API 401 Unauthorized: Invalid or expired token. "
                        f"Response: {response.text}"
                    )
                
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"Zendesk Sell API error: {e.response.text}")
                    raise RuntimeError(f"Zendesk Sell API request failed with status {e.response.status_code}")

                payload = response.json()
                items = payload.get("items", [])
                for item in items:
                    if "data" in item:
                        yield item["data"]

                # Pagination: follow meta.links.next_page
                meta = payload.get("meta", {})
                links = meta.get("links", {})
                url = links.get("next_page")
                params = None # Parameters are baked into next_page URL