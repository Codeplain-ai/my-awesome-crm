import os
import logging
from typing import Any, Callable, List
import httpx

from .mapping import map_streak_contact

logger = logging.getLogger(__name__)

# The data_type this integration primarily produces.
DATA_TYPE = "contact"

__all__ = ["DATA_TYPE", "fetch"]


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    :StreakIntegration: entry point.
    Pulls Contact records from Streak v2 REST API.
    """
    api_key = os.environ.get("STREAK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing STREAK_API_KEY environment variable")

    base_url = "https://api.streak.com/api/v2"
    auth = (api_key, "")
    
    produced_records = []

    with httpx.Client(auth=auth, timeout=30.0) as client:
        # 1. List Teams (the fan-out axis)
        try:
            teams_resp = client.get(f"{base_url}/users/me/teams")
            teams_resp.raise_for_status()
            teams = teams_resp.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"Streak API HTTP error listing teams: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error listing Streak teams: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

        if not isinstance(teams, list):
            error_msg = f"Unexpected Streak teams response format. Expected list, got {type(teams).__name__}: {teams}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # 2. List Contacts for each team
        for team in teams:
            team_key = team.get("key")
            if not team_key:
                continue
            
            try:
                contacts_resp = client.get(f"{base_url}/teams/{team_key}/contacts")
                contacts_resp.raise_for_status()
                streak_contacts = contacts_resp.json()
            except httpx.HTTPStatusError as e:
                error_msg = f"Streak API HTTP error for team {team_key}: {e.response.status_code} - {e.response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error fetching contacts for team {team_key}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)

            if not isinstance(streak_contacts, list):
                logger.warning(f"Streak contacts for team {team_key} not a list. Skipping. Type: {type(streak_contacts).__name__}")
                continue

            for sc in streak_contacts:
                mapped_data = map_streak_contact(sc)
                produced_records.append({
                    "data_type": "contact",
                    "data": mapped_data
                })

    return produced_records