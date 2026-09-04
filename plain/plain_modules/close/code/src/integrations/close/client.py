import httpx
from typing import Generator, List, Any

class CloseClient:
    BASE_URL = "https://api.close.com/api/v1"
    PAGE_SIZE = 100

    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_contacts(self) -> Generator[List[dict[str, Any]], None, None]:
        """
        Iterates through all contacts using offset-based pagination as per Close API.
        """
        skip = 0
        while True:
            # Authentication: API key as username, empty password
            auth = (self.api_key, "")
            params = {
                "_limit": self.PAGE_SIZE,
                "_skip": skip
            }
            
            try:
                response = httpx.get(
                    f"{self.BASE_URL}/contact/",
                    auth=auth,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise RuntimeError("Close API authentication failed: Invalid API Key")
                
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise RuntimeError(f"Close API transport error: {str(e)}") from e
            
            payload = response.json()
            data = payload.get("data", [])
            
            if not data:
                break
                
            yield data
            
            if not payload.get("has_more"):
                break
                
            skip += len(data)