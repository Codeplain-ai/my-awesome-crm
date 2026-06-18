import os
import httpx
from typing import Generator, Dict, Any, List

class CloseClient:
    """
    Minimal client for the Close REST API surface defined in openapi.yaml.
    """
    BASE_URL = "https://api.close.com/api/v1"

    def __init__(self):
        api_key = os.environ.get("CLOSE_API_KEY")
        if not api_key:
            raise RuntimeError("CLOSE_API_KEY")
        
        # Basic Auth: API Key as username, blank password
        self.auth = (api_key, "")
        self.limit = 100

    def list_contacts(self) -> Generator[Dict[str, Any], None, None]:
        """
        Iterates through all contacts using pagination.
        """
        skip = 0
        has_more = True

        with httpx.Client(base_url=self.BASE_URL, auth=self.auth) as client:
            while has_more:
                params = {
                    "_limit": self.limit,
                    "_skip": skip
                }
                response = client.get("/contact/", params=params)
                
                if response.status_code == 401:
                    raise RuntimeError("Close API authentication failed (401)")
                response.raise_for_status()
                
                data = response.json()
                records = data.get("data", [])
                for record in records:
                    yield record
                
                has_more = data.get("has_more", False)
                skip += len(records)
                
                # Safety break if no records returned but has_more is true
                if not records and has_more:
                    break