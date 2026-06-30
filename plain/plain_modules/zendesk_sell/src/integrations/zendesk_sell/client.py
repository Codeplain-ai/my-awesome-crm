import os
import logging
from typing import Any, Dict, Generator
import httpx

logger = logging.getLogger(__name__)

class ZendeskSellClient:
    """
    Client for interacting with the Zendesk Sell v2 REST API.
    """
    BASE_URL = "https://api.getbase.com"

    def __init__(self):
        token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
        if not token:
            error_msg = "Missing environment variable: ZENDESK_SELL_ACCESS_TOKEN"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "ZendeskSell-CRM-Integration/1.0"
        }

    def list_all_contacts(self) -> Generator[Dict[str, Any], None, None]:
        """
        Generator that yields individual items from the /v2/contacts endpoint,
        automatically following pagination links.
        """
        # OpenAPI spec pins per_page to 100.
        next_page_url = f"{self.BASE_URL}/v2/contacts?per_page=100"

        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            while next_page_url:
                try:
                    logger.debug(f"Fetching Zendesk Sell contacts: {next_page_url}")
                    response = client.get(next_page_url)
                    
                    if response.status_code != 200:
                        error_msg = (
                            f"Zendesk Sell API request failed with status {response.status_code}. "
                            f"URL: {next_page_url}, Response: {response.text}"
                        )
                        logger.error(error_msg)
                        response.raise_for_status()

                    payload = response.json()
                    
                    items = payload.get("items", [])
                    for item in items:
                        yield item

                    # Pagination: follow meta.links.next_page
                    meta = payload.get("meta", {})
                    links = meta.get("links", {})
                    next_page_url = links.get("next_page")

                except httpx.HTTPStatusError as e:
                    logger.error(f"Zendesk Sell API error: {e.response.status_code} - {e.response.text}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error calling Zendesk Sell API: {str(e)}")
                    raise