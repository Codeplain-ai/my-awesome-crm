from typing import Any, Dict, List, Optional
import httpx
from .config import get_api_token, get_company_domain

class PipedriveClient:
    """
    Minimal client for Pipedrive v1 REST API.
    Handles authentication and pagination.
    """
    def __init__(self):
        self.token = get_api_token()
        self.domain = get_company_domain()
        self.base_url = f"https://{self.domain}.pipedrive.com/v1"

    def list_persons(self, start: int = 0, limit: int = 100) -> Dict[str, Any]:
        params = {
            "api_token": self.token,
            "start": start,
            "limit": limit
        }
        response = httpx.get(f"{self.base_url}/persons", params=params, timeout=30.0)
        
        if response.status_code == 401:
            raise RuntimeError(
                f"Pipedrive authentication failed (HTTP 401). Check PIPEDRIVE_API_TOKEN. "
                f"Response body: {response.text}"
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Pipedrive API request failed with status {e.response.status_code}. "
                f"URL: {e.request.url}. Response: {e.response.text}"
            ) from e

        data = response.json()

        if not data.get("success"):
            error_msg = data.get("error", "Unknown Pipedrive error")
            error_info = data.get("error_info", "No additional info")
            raise RuntimeError(
                f"Pipedrive API returned success=false. Error: {error_msg}. Info: {error_info}"
            )
            
        return data