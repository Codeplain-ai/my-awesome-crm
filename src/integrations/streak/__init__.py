import os
import logging
import httpx
from typing import Any, List
from src.models.schemas import IncomingContact
from src.integrations.streak.mapping import map_streak_contact

__all__ = ["fetch_contacts"]

logger = logging.getLogger(__name__)

def get_credentials() -> str:
    """Reads STREAK_API_KEY from environment."""
    api_key = os.environ.get("STREAK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: STREAK_API_KEY")
    return api_key

def _make_request(url: str, auth: tuple[str, str]) -> Any:
    """
    Indirection seam for HTTP GET requests.
    """
    with httpx.Client(auth=auth, timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()

def fetch_contacts() -> List[dict[str, Any]]:
    """
    Main entry point for the Streak integration.
    Fetches contacts from all accessible teams and maps them.
    """
    api_key = get_credentials()
    auth = (api_key, "")
    base_url = "https://api.streak.com/api/v2"
    
    contacts_to_yield: List[dict[str, Any]] = []
    
    try:
        # 1. List Teams
        teams = _make_request(f"{base_url}/users/me/teams", auth)
        
        # 2. Iterate Teams
        for team in teams:
            team_key = team.get("key")
            if not team_key:
                continue
                
            # 3. List Contacts for Team
            raw_contacts = _make_request(f"{base_url}/teams/{team_key}/contacts", auth)
            
            # 4. Map records with skip-and-log policy
            for raw_record in raw_contacts:
                try:
                    incoming = map_streak_contact(raw_record)
                    # The host expects dicts that validate as IncomingContact
                    contacts_to_yield.append(incoming.model_dump())
                except ValueError as ve:
                    # Specific record failed validation/mapping
                    record_id = raw_record.get("key", "unknown")
                    logger.warning(
                        f"Skipping malformed Streak record {record_id} in team {team_key}: {str(ve)}"
                    )
                except Exception as e:
                    # Unexpected record processing error
                    record_id = raw_record.get("key", "unknown")
                    logger.error(
                        f"Unexpected error mapping Streak record {record_id}: {str(e)}"
                    )
    except httpx.HTTPStatusError:
        raise

    return contacts_to_yield