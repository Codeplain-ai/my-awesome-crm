import os
import logging
import httpx
from typing import Generator, Any, Dict

logger = logging.getLogger(__name__)

class NimbleClient:
    """Client for the Nimble REST API v1."""
    
    BASE_URL = "https://app.nimble.com/api/v1"
    PAGE_SIZE = 30

    def __init__(self):
        self.access_token = os.environ.get("NIMBLE_ACCESS_TOKEN")
        if not self.access_token:
            # Requirement: Raise RuntimeError naming the env var key if missing.
            raise RuntimeError("Missing or empty environment variable: NIMBLE_ACCESS_TOKEN")

    def list_person_contacts(self) -> Generator[Dict[str, Any], None, None]:
        """
        Iterates through all person contacts using pagination based on the 
        meta.page and meta.pages counters in the response.
        """
        page = 1
        
        with httpx.Client(base_url=self.BASE_URL, timeout=30.0) as client:
            while True:
                logger.debug(f"Fetching Nimble contacts page {page}")
                
                try:
                    response = client.get(
                        "/contacts",
                        params={
                            "record_type": "person",
                            "per_page": self.PAGE_SIZE,
                            "page": page
                        },
                        headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "Accept": "application/json"
                        }
                    )
                    
                    if response.status_code == 401:
                        raise RuntimeError("Nimble API authentication failed (401 Unauthorized)")
                    
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error(f"HTTP transport error during Nimble fetch: {str(e)}")
                    raise RuntimeError(f"Nimble API transport error: {str(e)}")
                
                payload = response.json()
                
                resources = payload.get("resources", [])
                for record in resources:
                    yield record
                
                meta = payload.get("meta", {})
                current_page = meta.get("page")
                total_pages = meta.get("pages")
                
                # Pagination termination: stop if no resources, or we've reached the last page.
                if not resources or current_page is None or total_pages is None or current_page >= total_pages:
                    break
                    
                page = current_page + 1