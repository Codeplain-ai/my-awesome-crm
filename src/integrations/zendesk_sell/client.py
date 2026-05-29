import os
import requests
from typing import Any, Iterable
from src.integrations.zendesk_sell.mapping import zendesk_sell_contact_to_incoming

def _get(url: str, access_token: str, params: dict) -> dict[str, Any]:
    """
    Indirection point for HTTP GET to Zendesk Sell.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if not (200 <= response.status_code < 300):
        raise RuntimeError(
            f"Integration failed: Zendesk Sell API returned {response.status_code} "
            f"for URL {url}. Response: {response.text}"
        )
    return response.json()

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Fetches person-type contacts from Zendesk Sell and returns a list of IncomingContact dicts.
    """
    access_token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Missing required environment variable: ZENDESK_SELL_ACCESS_TOKEN")

    api_base = os.environ.get("ZENDESK_SELL_API_BASE", "https://api.getbase.com/v2")
    url = f"{api_base.rstrip('/')}/contacts"

    all_incoming_contacts = []
    page = 1
    per_page = 100

    while True:
        params = {"page": page, "per_page": per_page}
        data = _get(url, access_token, params)
        items = data.get("items", [])

        for envelope in items:
            contact_data = envelope.get("data", {})
            # Unified :Contact: model is person-only. Skip organizations.
            if contact_data.get("is_organization"):
                continue

            incoming = zendesk_sell_contact_to_incoming(contact_data)
            all_incoming_contacts.append(incoming)

        # Stop if page is empty or we received fewer items than requested (end of collection)
        if not items or len(items) < per_page:
            break

        page += 1

    return all_incoming_contacts