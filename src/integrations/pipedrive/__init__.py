"""Pipedrive integration entry point and public mapping utility."""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.parse import urljoin

import requests

from .mapping import map_contact

logger = logging.getLogger(__name__)

DATA_TYPE = "contact"
_PAGE_SIZE = 100
_REQUEST_TIMEOUT_SECONDS = 30
_DOMAIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")


def _get_credentials() -> tuple[str, str]:
    """Read and validate the Pipedrive company subdomain and API token."""
    values: list[str] = []
    for key in ("PIPEDRIVE_API_TOKEN", "PIPEDRIVE_COMPANY_DOMAIN"):
        value = os.environ.get(key)
        if value is None or not value.strip():
            raise RuntimeError(f"Required environment variable {key} is missing or empty")
        values.append(value.strip())

    token, company_domain = values
    if not _DOMAIN_PATTERN.fullmatch(company_domain):
        raise RuntimeError(
            "Environment variable PIPEDRIVE_COMPANY_DOMAIN must be a company "
            "subdomain containing only letters, digits, and hyphens"
        )
    return token, company_domain


def _request_page(
    company_domain: str, api_token: str, start: int | None = None
) -> dict[str, Any]:
    """Fetch one persons page; this is the sole provider HTTP access seam."""
    url = f"https://{company_domain}.pipedrive.com/v1/persons"
    params: dict[str, Any] = {"api_token": api_token, "limit": _PAGE_SIZE}
    if start is not None:
        params["start"] = start

    response = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    try:
        body = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError) as exc:
        raise RuntimeError(f"Pipedrive persons endpoint returned invalid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise RuntimeError(
            "Pipedrive persons endpoint returned an invalid response envelope "
            f"(expected object, got {type(body).__name__})"
        )
    return body


def _person_pages(company_domain: str, api_token: str):
    """Yield all person records while validating the v1 offset pagination envelope."""
    start: int | None = None
    visited_starts: set[int] = set()
    while True:
        envelope = _request_page(company_domain, api_token, start)
        if envelope.get("success") is not True:
            # Never include the request URL or token in diagnostics.
            raise RuntimeError(
                "Pipedrive persons request failed: "
                f"{envelope.get('error', 'response success was not true')}"
            )

        records = envelope.get("data")
        if records is None:
            records = []
        if not isinstance(records, list):
            raise RuntimeError(
                "Pipedrive persons response field 'data' must be an array or null; "
                f"got {type(records).__name__}"
            )
        yield from records

        additional_data = envelope.get("additional_data")
        pagination = (
            additional_data.get("pagination")
            if isinstance(additional_data, dict)
            else None
        )
        more_items = (
            pagination.get("more_items_in_collection")
            if isinstance(pagination, dict)
            else False
        )
        if more_items is not True:
            return

        next_start = pagination.get("next_start")
        if isinstance(next_start, bool) or not isinstance(next_start, int):
            raise RuntimeError(
                "Pipedrive pagination indicates more records but does not provide "
                f"a valid integer next_start: {next_start!r}"
            )
        if next_start in visited_starts or next_start == start:
            raise RuntimeError(
                f"Pipedrive pagination returned a repeated start offset: {next_start}"
            )
        visited_starts.add(next_start)
        start = next_start


def fetch(get_stored) -> list[dict[str, Any]]:
    """Retrieve and map all Pipedrive persons into host-compatible records.

    ``get_stored`` is part of the host plug-in contract. This integration does
    not need stored values, but accepts the callback to remain interchangeable
    with integrations that use it.
    """
    del get_stored  # Deliberately unused: Pipedrive is read as a complete batch.
    api_token, company_domain = _get_credentials()

    output: list[dict[str, Any]] = []
    for person in _person_pages(company_domain, api_token):
        identifier = person.get("id") if isinstance(person, dict) else None
        try:
            contact = map_contact(person)
        except ValueError as exc:
            logger.warning(
                "Skipping Pipedrive person %r because contact mapping failed: %s",
                identifier,
                exc,
            )
            continue
        output.append({"data_type": DATA_TYPE, "data": contact})
    return output


__all__ = ["DATA_TYPE", "fetch", "map_contact"]
