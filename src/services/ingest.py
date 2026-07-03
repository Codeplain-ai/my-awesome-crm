import importlib
import logging
import os
import pathlib
from datetime import datetime, timezone
from typing import Any, Callable, List

from sqlmodel import Session

from src.models.db import Record
from src.repositories.record_repo import RecordRepository

logger = logging.getLogger(__name__)

# The data_type a discovered integration falls back to when it does not declare
# one explicitly via a module-level DATA_TYPE attribute.
DEFAULT_DATA_TYPE = "contact"

# The payload field that carries a record's stable, provider-side identity. Rows
# are matched on (source, data_type, IDENTITY_FIELD) so a re-sync can update an
# existing record in place instead of deleting and re-inserting it. Every
# integration's mapping emits this field.
IDENTITY_FIELD = "external_id"


def _identity_key(data_type: str, payload: Any):
    """Stable identity for a produced record within one integration.

    Returns a (data_type, identity_value) tuple, or None when the payload has no
    usable identity. An unidentifiable record cannot be matched to an existing
    row, so the caller always inserts it (the host never deletes).
    """
    if isinstance(payload, dict):
        value = payload.get(IDENTITY_FIELD)
        if value is not None and value != "":
            return (data_type, value)
    return None


def get_integrations_base_path() -> pathlib.Path:
    """
    Returns the path to the integrations directory.
    Supports override via CRM_INTEGRATIONS_PATH for testing.
    """
    env_path = os.environ.get("CRM_INTEGRATIONS_PATH")
    if env_path:
        return pathlib.Path(env_path)
    return pathlib.Path(__file__).parent.parent / "integrations"


def discover_integrations() -> List[str]:
    """
    Scans the integrations directory and returns identifiers of valid integrations.
    A valid integration is a directory (not starting with _) containing an __init__.py
    and exporting a 'fetch' callable.
    """
    base_path = get_integrations_base_path()
    discovered = []

    if not base_path.exists() or not base_path.is_dir():
        logger.warning(f"Integrations directory not found at {base_path}")
        return []

    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            if not (item / "__init__.py").exists():
                continue
            try:
                module_name = f"src.integrations.{item.name}"
                module = importlib.import_module(module_name)
                fetch_fn = getattr(module, "fetch", None)
                if fetch_fn and callable(fetch_fn):
                    discovered.append(item.name)
                    logger.info(f"Discovered integration: {item.name}")
                else:
                    logger.warning(f"Integration '{item.name}' missing 'fetch' callable")
            except Exception as e:
                logger.error(
                    f"Failed to import integration '{item.name}'",
                    extra={"error": str(e)},
                )

    return discovered


def run_integration_service(session: Session, integration_name: str) -> dict[str, Any]:
    """
    Runs the named integration and stores its output.

    The integration exposes a `fetch(get_stored)` callable. `get_stored` is a
    callback the integration may call with a data_type to read every row already
    stored for that type. `fetch` returns a list of records; each record is a
    dict carrying a `data_type` and a `data` payload, so a single integration may
    emit several kinds of record (e.g. both "contact" and "account"). The host
    stores each `data` payload verbatim under its own `data_type`.

    For backwards tolerance, a bare payload dict (no `data_type`/`data` keys) is
    stored under the integration's module-level DATA_TYPE, falling back to
    DEFAULT_DATA_TYPE.

    Storage is an upsert keyed on (source, data_type, external_id): a produced
    record that matches an existing row updates that row in place (only when its
    data actually changed), an unmatched record is inserted, and nothing is ever
    deleted. Re-syncing is therefore idempotent — an unchanged record produces
    no write. The returned counts reflect this: `stored` is the number of new
    rows inserted, `replaced` the number of existing rows whose data changed, and
    `unchanged` the number left untouched.
    """
    base_path = get_integrations_base_path()
    item = base_path / integration_name

    if not item.is_dir() or item.name.startswith("_") or not (item / "__init__.py").exists():
        raise ValueError(f"Unknown integration: {integration_name}")

    try:
        module_name = f"src.integrations.{integration_name}"
        module = importlib.import_module(module_name)
        fetch_fn = getattr(module, "fetch", None)
        if not fetch_fn or not callable(fetch_fn):
            raise ValueError(f"Unknown integration: {integration_name}")
    except (ImportError, AttributeError):
        raise ValueError(f"Unknown integration: {integration_name}")

    default_data_type = getattr(module, "DATA_TYPE", DEFAULT_DATA_TYPE)
    repo = RecordRepository(session)

    def get_stored(requested_type: str) -> list[dict[str, Any]]:
        """Callback handed to the integration: all stored rows of a data_type."""
        return [
            {
                "id": r.id,
                "data_type": r.data_type,
                "source": r.source,
                "data": r.data,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in repo.list_by_type(requested_type)
        ]

    try:
        produced = fetch_fn(get_stored)
        if produced is None:
            produced = []

        now = datetime.now(timezone.utc)

        # Index this integration's existing rows by identity so we can upsert:
        # update a matching row in place, insert a new one, delete nothing.
        existing_index: dict[tuple[str, Any], Record] = {}
        for row in repo.list_by_source(integration_name):
            key = _identity_key(row.data_type, row.data)
            if key is not None:
                existing_index[key] = row

        inserted = 0
        updated = 0
        unchanged = 0
        type_counts: dict[str, int] = {}
        for item in produced:
            if isinstance(item, dict) and "data_type" in item and "data" in item:
                row_type = item["data_type"] or default_data_type
                payload = item["data"]
            else:
                # Bare payload: store under the module default data_type.
                row_type = default_data_type
                payload = item
            type_counts[row_type] = type_counts.get(row_type, 0) + 1

            key = _identity_key(row_type, payload)
            existing = existing_index.get(key) if key is not None else None

            if existing is not None:
                # Known record: update in place only if the data actually changed.
                if existing.data != payload:
                    existing.data = payload
                    existing.updated_at = now
                    session.add(existing)
                    updated += 1
                else:
                    unchanged += 1
            else:
                # New record: insert it. Nothing is deleted.
                new_row = Record(
                    data_type=row_type,
                    source=integration_name,
                    data=payload,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_row)
                inserted += 1
                # Track it so a duplicate identity later in the same batch updates
                # this row rather than inserting a second copy.
                if key is not None:
                    existing_index[key] = new_row

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Integration '{integration_name}' failed: {str(e)}", exc_info=True)
        raise RuntimeError(f"Integration failed: {str(e)}")

    return {
        "integration": integration_name,
        "data_types": type_counts,
        "fetched": len(produced),
        "stored": inserted,
        "replaced": updated,
        "unchanged": unchanged,
    }
