import httpx
from typing import Generator, Any

class NimbleClient:
    """
    Client for Nimble REST API v1.
    Handles authentication and pagination.
    """
    BASE_URL = "https://app.nimble.com/api/v1"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

    def list_person_contacts(self, per_page: int = 30) -> Generator[dict[str, Any], None, None]:
        """
        Yields raw contact records from Nimble by paginating through the list endpoint.
        Filters for record_type=person.
        """
        page = 1
        while True:
            params = {
                "record_type": "person",
                "per_page": per_page,
                "page": page
            }
            
            with httpx.Client(base_url=self.BASE_URL, headers=self.headers) as client:
                response = client.get("/contacts", params=params)
                
                if response.status_code == 401:
                    raise RuntimeError("Nimble API authentication failed (401 Unauthorized)")
                
                response.raise_for_status()
                data = response.json()
                
                resources = data.get("resources", [])
                for record in resources:
                    yield record
                
                meta = data.get("meta", {})
                current_page = meta.get("page")
                total_pages = meta.get("pages")
                
                # Stop if no resources returned or we reached/exceeded the last page
                if not resources or current_page is None or total_pages is None or current_page >= total_pages:
                    break
                    
                page += 1