import logging
import os
from typing import Any, Callable, List, Dict

from .client import StreakClient
from .mapping import map_contact

logger = logging.getLogger(__name__)

# Provider identifier
DATA_TYPE = "contact"

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Entry point for the Streak integration.
    """
    api_key = os.environ.get("STREAK_API_KEY")
    if not api_key or api_key.strip() == "":
        logger.error("STREAK_API_KEY environment variable is missing or empty")
        raise RuntimeError("Missing STREAK_API_KEY")

    client = StreakClient(api_key.strip())
    
    try:
        teams = client.list_teams()
    except Exception as e:
        logger.error(f"Failed to list teams from Streak: {e}")
        raise RuntimeError(f"Streak connection failed: {e}")

    all_produced = []

    for team in teams:
        team_key = team.get("key")
        if not team_key:
            continue
            
        try:
            raw_contacts = client.list_contacts(team_key)
        except Exception as e:
            logger.error(f"Failed to fetch contacts for team {team_key}: {e}")
            raise RuntimeError(f"Streak API error: {e}")

        for raw_record in raw_contacts:
            external_id = raw_record.get("key", "unknown")
            try:
                mapped_data = map_contact(raw_record)
                all_produced.append({
                    "data_type": "contact",
                    "data": mapped_data
                })
            except ValueError as ve:
                logger.warning(
                    f"Skipping record {external_id} in Streak integration due to mapping error: {ve}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error mapping record {external_id}: {e}", 
                    exc_info=True
                )
                # We skip unexpected errors as per the skip-and-log batch policy
                continue

    return all_produced