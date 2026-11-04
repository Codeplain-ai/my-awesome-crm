"""Pure transformation from a Pipedrive v1 person to the conventional contact shape."""

from __future__ import annotations

from typing import Any

_PROVIDER_ID = "pipedrive"
_CONSUMED_FIELDS = frozenset(
    {
        "id",
        "name",
        "first_name",
        "last_name",
        "email",
        "job_title",
        "org_id",
        "org_name",
        # Pipedrive includes this field on person records, but the mapping
        # contract intentionally does not retain phone information.
        "phone",
    }
)
# These belong to API response envelopes, not to an individual person's
# provider-specific custom fields.
_ENVELOPE_FIELDS = frozenset({"success", "data", "additional_data"})


def _nonempty_string(value: Any) -> str | None:
    """Return a trimmed, non-empty string; treat malformed values as absent."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _full_name(record: dict[str, Any]) -> str:
    name = _nonempty_string(record.get("name"))
    if name is not None:
        return name

    first_name = _nonempty_string(record.get("first_name")) or ""
    last_name = _nonempty_string(record.get("last_name")) or ""
    return " ".join(part for part in (first_name, last_name) if part).strip()


def _primary_email(raw_emails: Any) -> str | None:
    """Choose and normalize the primary (or first) address from email[]."""
    if not isinstance(raw_emails, (list, tuple)) or not raw_emails:
        return None

    entries = [entry for entry in raw_emails if isinstance(entry, dict)]
    if not entries:
        return None

    selected = next((entry for entry in entries if entry.get("primary") is True), entries[0])
    value = selected.get("value")
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value or None


def _company_name(record: dict[str, Any]) -> str | None:
    flat_name = _nonempty_string(record.get("org_name"))
    if flat_name is not None:
        return flat_name

    organization = record.get("org_id")
    if isinstance(organization, dict):
        return _nonempty_string(organization.get("name"))
    return None


def map_contact(record: Any) -> dict[str, Any]:
    """Map one Pipedrive v1 person record to the conventional contact shape.

    Mapping is deliberately best-effort: missing or malformed person fields are
    represented by ``None`` (or an empty ``full_name``), and never prevent a
    contact from being produced. The input is not modified.

    Args:
        record: A dict shaped like one entry of the Pipedrive ``data`` array.

    Returns:
        A contact dict containing exactly the fields defined by the mapping
        contract.
    """
    source = record if isinstance(record, dict) else {}

    raw_id = source.get("id")
    external_id = None if raw_id is None else str(raw_id)

    raw_job_title = source.get("job_title")
    job_title = None if raw_job_title is None or raw_job_title == "" else raw_job_title

    custom_fields = {
        key: value
        for key, value in source.items()
        if key not in _CONSUMED_FIELDS and key not in _ENVELOPE_FIELDS
    }

    return {
        "provider_id": _PROVIDER_ID,
        "external_id": external_id,
        "full_name": _full_name(source),
        "primary_email": _primary_email(source.get("email")),
        "job_title": job_title,
        "company_name": _company_name(source),
        "custom_fields": custom_fields,
    }
