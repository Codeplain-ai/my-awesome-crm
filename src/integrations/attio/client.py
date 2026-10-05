import os
import httpx
from typing import Any, Dict

class AttioClient:
    """
    Thin wrapper around Attio REST API to facilitate testing.
    Reads ATTIO_ACCESS_TOKEN from environment.
    """
    BASE_URL = "https://api.attio.com/v2"

    def __init__(self):
        self.token = os.environ.get("ATTIO_ACCESS_TOKEN")
        if not self.token:
            raise RuntimeError("Missing environment variable: ATTIO_ACCESS_TOKEN")

    def query_people(self, offset: int = 0, limit: int = 500) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "limit": limit,
            "offset": offset,
            "sorts": [
                {"direction": "asc", "attribute": "created_at", "field": "value"}
            ]
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.BASE_URL}/objects/people/records/query",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()