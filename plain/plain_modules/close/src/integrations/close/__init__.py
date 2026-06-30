import logging
import os
from typing import Any, Callable, List, Dict

import httpx

from .mapping import map_close_contact

logger = logging.getLogger(__name__)

# The data_type this integration produces.
DATA_TYPE = "contact"

__all__ = ["DATA_TYPE", "fetch"]

def fetch(get_stored: Callable[[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Fetches contacts from the Close REST API and maps them to the host's Contact format.
    
    Args:
        get_stored: A callback to retrieve existing records (unused in this specific pull).
        
    Returns:
        A list of dicts, each containing 'data_type' and 'data' (the mapped contact).
    """
    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: CLOSE_API_KEY")

    base_url = "https://api.close.com/api/v1/contact/"
    # Close uses Basic Auth with API Key as username and blank password
    auth = (api_key, "")
    limit = 100
    skip = 0
    results = []

    try:
        with httpx.Client(auth=auth, timeout=60.0) as client:
            has_more = True
            while has_more:
                params = {"_limit": limit, "_skip": skip}
                response = client.get(base_url, params=params)

                if response.status_code == 401:
                    raise RuntimeError(
                        f"Authentication failed for Close API. Check CLOSE_API_KEY. "
                        f"Response: {response.text}"
                    )
                
                if response.status_code != 200:
                    logger.error(
                        "Unexpected response from Close API",
                        extra={"status_code": response.status_code, "body": response.text, "skip": skip}
                    )
                    response.raise_for_status()

                page_data = response.json()
                contacts = page_data.get("data", [])
                
                for contact in contacts:
                    mapped = map_close_contact(contact)
                    results.append({
                        "data_type": DATA_TYPE,
                        "data": mapped
                    })

                has_more = page_data.get("has_more", False)
                if has_more:
                    skip += len(contacts)
                    # Safety check to prevent infinite loops if API behaves unexpectedly
                    if len(contacts) == 0:
                        logger.warning("Close API reported 'has_more' but returned 0 records. Breaking.")
                        break

    except httpx.RequestError as exc:
        msg = f"An error occurred while requesting {exc.request.url!r}: {exc}"
        logger.error(msg, exc_info=True)
        raise RuntimeError(f"Transport/HTTP error connecting to Close: {str(exc)}")

    return results