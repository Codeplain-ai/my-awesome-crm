import os
from typing import Any, Dict, Generator, Optional
import httpx

class NimbleClient:
    """
    Minimal client for the Nimble REST API v1.
    """
    BASE_URL = "https://app.nimble.com/api/v1"
    
    def __init__(self, access_token: Optional[str] = None):
        token = access_token or os.environ.get("NIMBLE_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("NIMBLE_ACCESS_TOKEN")

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    def list_contacts_page(self, record_type: str = "person", page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """Fetches a single page of contacts."""
        params = {
            "record_type": record_type,
            "page": page,
            "per_page": per_page
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{self.BASE_URL}/contacts", params=params, headers=self.headers)
                if response.status_code == 401:
                    raise RuntimeError(f"Nimble API authentication failed (401): {response.status_code} - {response.text}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP request to Nimble failed: {str(e)}")

    def list_all_contacts(self, record_type: str = "person") -> Generator[Dict[str, Any], None, None]:
        """
        Paginates through all available contacts.
        Follows meta.page and meta.pages counters.
        """
        current_page = 1
        per_page = 30
        
        while True:
            data = self.list_contacts_page(record_type=record_type, page=current_page, per_page=per_page)
            resources = data.get("resources", [])
            meta = data.get("meta", {})
            
            for record in resources:
                yield record
            
            total_pages = meta.get("pages", 1)
            actual_page = meta.get("page", current_page)
            
            if actual_page >= total_pages or not resources:
                break
            
            current_page = actual_page + 1