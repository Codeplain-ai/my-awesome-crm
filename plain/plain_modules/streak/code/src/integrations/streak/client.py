import httpx
from typing import Any, List, Dict

class StreakClient:
    """
    Simple HTTP client for the Streak v2 API.
    """
    BASE_URL = "https://api.streak.com/api/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str) -> Any:
        # Streak uses Basic Auth with the API key as the username and empty password
        auth = (self.api_key, "")
        try:
            response = httpx.get(
                f"{self.BASE_URL}{path}",
                auth=auth,
                timeout=30.0,
                follow_redirects=True
            )
        except httpx.RequestError as exc:
            raise RuntimeError(f"An error occurred while requesting {exc.request.url!r}: {exc}")

        if response.status_code == 401:
            raise RuntimeError(
                f"Streak API returned 401 Unauthorized for path {path}. "
                "Ensure STREAK_API_KEY is valid."
            )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Streak API returned unexpected status {response.status_code} "
                f"for path {path}: {response.text}"
            )

        return response.json()

    def list_teams(self) -> List[Dict[str, Any]]:
        """GET /api/v2/users/me/teams"""
        data = self._get("/users/me/teams")
        if not isinstance(data, list):
            return []
        return data

    def list_contacts(self, team_key: str) -> List[Dict[str, Any]]:
        """GET /api/v2/teams/{teamKey}/contacts"""
        data = self._get(f"/teams/{team_key}/contacts")
        if not isinstance(data, list):
            return []
        return data