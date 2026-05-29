import os
from typing import Iterable, Any
from hubspot import HubSpot
from src.integrations.hubspot.mapping import hubspot_contact_to_incoming

def _get_client(access_token: str, base_url: str | None = None) -> HubSpot:
    """Indirection point for building the HubSpot client."""
    kwargs = {"access_token": access_token}
    if base_url:
        kwargs["base_url"] = base_url
    return HubSpot(**kwargs)

def _fetch_page(client: HubSpot, after: str | None = None) -> Any:
    """Indirection point for the HubSpot API call."""
    # We fetch the standard properties used in mapping
    properties = ["firstname", "lastname", "email", "phone", "jobtitle", "company"]
    return client.crm.contacts.basic_api.get_page(
        limit=100, 
        after=after, 
        properties=properties
    )

def fetch_contacts() -> Iterable[dict[str, Any]]:
    """
    Pulls contacts from HubSpot and yields IncomingContact dicts.
    Reads credentials from environment variables on every call.
    """
    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Missing required environment variable: HUBSPOT_ACCESS_TOKEN")
    
    base_url = os.environ.get("HUBSPOT_API_BASE")
    client = _get_client(access_token, base_url)
    
    after = None
    while True:
        try:
            page = _fetch_page(client, after)
        except Exception as e:
            raise RuntimeError(f"HubSpot API request failed: {str(e)}") from e
            
        for contact_obj in page.results:
            # SimplePublicObject returned by the lib can be converted to dict
            yield hubspot_contact_to_incoming(contact_obj.to_dict())
            
        if page.paging and page.paging.next:
            after = page.paging.next.after
        else:
            break