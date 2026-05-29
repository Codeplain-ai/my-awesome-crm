import os
from typing import Iterable, Any
from hubspot import HubSpot
from src.integrations.hubspot.mapping import hubspot_contact_to_incoming

def _build_client(access_token: str, base_url: str | None = None) -> HubSpot:
    """Indirection point for building the HubSpot client."""
    client = HubSpot(access_token=access_token)
    if base_url:
        client.api_client.configuration.host = base_url
    return client

def _get_page(client: HubSpot, after: str | None, properties: list[str]) -> Any:
    """Indirection point for the HubSpot API call."""
    return client.crm.contacts.basic_api.get_page(
        limit=100,
        after=after,
        properties=properties
    )

def _to_dict(obj: Any) -> dict[str, Any]:
    """Indirection point for converting HubSpot objects to dict."""
    return obj.to_dict()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Pulls contacts from HubSpot and returns a list of IncomingContact dicts.
    Reads credentials from environment variables on every call.
    """
    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Missing required environment variable: HUBSPOT_ACCESS_TOKEN")

    base_url = os.environ.get("HUBSPOT_API_BASE")
    client = _build_client(access_token, base_url)
    
    properties = ["firstname", "lastname", "email", "phone", "jobtitle", "company"]
    incoming_contacts = []
    after = None

    while True:
        try:
            page = _get_page(client, after, properties)
        except Exception as e:
            raise RuntimeError(f"HubSpot API request failed: {str(e)}") from e

        for contact_obj in (page.results or []):
            raw_dict = _to_dict(contact_obj)
            incoming_contacts.append(hubspot_contact_to_incoming(raw_dict))

        if page.paging and page.paging.next and page.paging.next.after:
            after = page.paging.next.after
        else:
            break

    return incoming_contacts