import os
import httpx
from typing import Any, List, Optional

class DynamicsClient:
    """
    HTTP client for Dynamics 365 (Dataverse) Web API.
    Handles OAuth2 authentication and paginated contact retrieval.
    """

    def __init__(self):
        self.endpoint = os.environ.get("DYNAMICS_ENDPOINT")
        self.tenant_id = os.environ.get("DYNAMICS_TENANT_ID")
        self.client_id = os.environ.get("DYNAMICS_CLIENT_ID")
        self.client_secret = os.environ.get("DYNAMICS_CLIENT_SECRET")

        for key, val in [
            ("DYNAMICS_ENDPOINT", self.endpoint),
            ("DYNAMICS_TENANT_ID", self.tenant_id),
            ("DYNAMICS_CLIENT_ID", self.client_id),
            ("DYNAMICS_CLIENT_SECRET", self.client_secret),
        ]:
            if not val:
                raise RuntimeError(f"Missing environment variable: {key}")

        self.endpoint = self.endpoint.rstrip("/")

    def _get_token(self) -> str:
        """Acquires a bearer token via client_credentials flow."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        scope = f"{self.endpoint}/.default"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
        }
        
        with httpx.Client() as client:
            resp = client.post(url, data=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to acquire Dynamics token: {resp.status_code} {resp.text}")
            return resp.json()["access_token"]

    def list_contacts(self) -> List[dict[str, Any]]:
        """Fetches all contacts, following @odata.nextLink pagination."""
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

        # Initial query parameters as defined in openapi.yaml
        params = {
            "$select": "contactid,fullname,firstname,lastname,emailaddress1,jobtitle",
            "$expand": "parentcustomerid_account($select=name)",
        }

        url = f"{self.endpoint}/api/data/v9.2/contacts"
        all_records = []

        try:
            with httpx.Client(headers=headers, timeout=30.0) as client:
                while url:
                    # On subsequent pages, nextLink is absolute and contains its own params
                    request_params = params if "?" not in url else None
                    resp = client.get(url, params=request_params)

                    if resp.status_code != 200:
                        raise RuntimeError(
                            f"Dynamics API request failed with status {resp.status_code}: {resp.text}"
                        )

                    data = resp.json()
                    page_values = data.get("value")
                    if not isinstance(page_values, list):
                        raise RuntimeError(f"Unexpected API response format: 'value' key missing or not a list. Body: {resp.text}")

                    all_records.extend(page_values)
                    # Pagination: follow @odata.nextLink verbatim if present
                    url = data.get("@odata.nextLink")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Transport error while querying Dynamics at {exc.request.url!r}: {exc}")

        return all_records