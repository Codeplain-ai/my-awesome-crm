from typing import Any, Generator
import httpx

class HubSpotClient:
    """
    Minimal client for the HubSpot REST API surface.
    """
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def list_contacts(self) -> Generator[dict[str, Any], None, None]:
        """
        Generator that yields contact records, handling pagination.
        """
        url = f"{self.BASE_URL}/crm/v3/objects/contacts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params: dict[str, Any] = {
            "limit": 100,
            "properties": "firstname,lastname,email,jobtitle,company"
        }

        with httpx.Client() as client:
            while True:
                response = client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        message = error_data.get("message", response.text)
                    except Exception:
                        message = response.text
                    raise RuntimeError(f"HubSpot API error ({response.status_code}): {message}")

                data = response.json()
                for record in data.get("results", []):
                    yield record

                # Pagination
                after = data.get("paging", {}).get("next", {}).get("after")
                if not after:
                    break
                params["after"] = after
