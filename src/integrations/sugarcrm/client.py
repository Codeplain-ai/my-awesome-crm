import os
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

class SugarCrmClient:
    """
    Client for :SugarCrmRestAPI: implementing OAuth 2.0 password grant and pagination.
    """
    def __init__(self):
        required_vars = [
            "SUGARCRM_ENDPOINT",
            "SUGARCRM_CLIENT_ID",
            "SUGARCRM_CLIENT_SECRET",
            "SUGARCRM_USERNAME",
            "SUGARCRM_PASSWORD",
        ]
        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise RuntimeError(f"Missing required environment variable: {missing[0]}")

        self.endpoint = os.environ.get("SUGARCRM_ENDPOINT", "").rstrip("/")
        self.client_id = os.environ.get("SUGARCRM_CLIENT_ID")
        self.client_secret = os.environ.get("SUGARCRM_CLIENT_SECRET")
        self.username = os.environ.get("SUGARCRM_USERNAME")
        self.password = os.environ.get("SUGARCRM_PASSWORD")

    def _get_token(self) -> str:
        url = f"{self.endpoint}/rest/v11/oauth2/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "platform": "base",
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                if response.status_code != 200:
                    logger.error(f"SugarCRM auth failed: {response.status_code} {response.text}")
                    response.raise_for_status()
                return response.json()["access_token"]
        except Exception as e:
            logger.error(f"Failed to acquire SugarCRM token: {str(e)}", exc_info=True)
            raise

    def fetch_contacts_page(self, token: str, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Fetches one page of contacts and returns (records, next_offset)."""
        url = f"{self.endpoint}/rest/v11/Contacts"
        params = {
            "fields": "id,first_name,last_name,name,full_name,email,email1,title,account_name,date_entered,date_modified",
            "max_num": 200,
            "order_by": "date_entered:asc",
        }
        if offset > 0:
            params["offset"] = offset

        headers = {"OAuth-Token": token}
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.error(f"SugarCRM API call failed: {response.status_code} {response.text}")
                    response.raise_for_status()
                
                data = response.json()
                records = data.get("records", [])
                next_offset = data.get("next_offset", -1)
                return records, next_offset
        except Exception as e:
            logger.error(f"Failed to fetch SugarCRM contacts at offset {offset}: {str(e)}", exc_info=True)
            raise