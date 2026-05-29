import importlib
import logging
import os
import pathlib
from datetime import datetime
from typing import List, Callable, Any
from src.models.schemas import IncomingContact
from src.models.db import Contact, SourceLink
from src.repositories.contact_repo import ContactRepository
from src.repositories.source_link_repo import SourceLinkRepository
from src.services.dedup import compute_dedup_key, merge_contact_data
from sqlmodel import Session

logger = logging.getLogger(__name__)

def get_integrations_base_path() -> pathlib.Path:
    """
    Returns the path to the integrations directory.
    Supports override via CRM_INTEGRATIONS_PATH for testing.
    """
    env_path = os.environ.get("CRM_INTEGRATIONS_PATH")
    if env_path:
        return pathlib.Path(env_path)
    
    # Default to src/integrations/ relative to this file
    return pathlib.Path(__file__).parent.parent / "integrations"

def discover_integrations() -> List[str]:
    """
    Scans the integrations directory and returns identifiers of valid integrations.
    A valid integration is a directory (not starting with _) containing an __init__.py
    and exporting a 'fetch_contacts' callable.
    """
    base_path = get_integrations_base_path()
    discovered = []

    if not base_path.exists() or not base_path.is_dir():
        logger.warning(f"Integrations directory not found at {base_path}")
        return []

    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check for __init__.py to ensure it's a package
            if not (item / "__init__.py").exists():
                continue
            
            try:
                # Construct module path. 
                # If using the default path, it's src.integrations.<name>
                # If using override, we might need to handle sys.path
                module_name = f"src.integrations.{item.name}"
                
                # If overridden, we need to ensure the parent is in sys.path
                # but for standard src/ layout, src is usually the root.
                module = importlib.import_module(module_name)
                
                # Check for contract: fetch_contacts callable
                fetch_fn = getattr(module, "fetch_contacts", None)
                if fetch_fn and callable(fetch_fn):
                    discovered.append(item.name)
                    logger.info(f"Discovered integration: {item.name}")
                else:
                    logger.warning(f"Integration '{item.name}' missing 'fetch_contacts' callable")
            
            except Exception as e:
                logger.error(
                    f"Failed to import integration '{item.name}'", 
                    extra={"error": str(e)}
                )
                
    return discovered

def persist_incoming_contact(
    session: Session, 
    incoming: IncomingContact
) -> tuple[Contact, bool]:
    """
    Dedupes and persists an IncomingContact.
    Returns a tuple of (Contact, created) where created is True if a new record was made.
    """
    contact_repo = ContactRepository(session)
    link_repo = SourceLinkRepository(session)
    
    dedup_key = compute_dedup_key(incoming)
    existing_contact: Contact | None = None
    
    if dedup_key:
        if "@" in dedup_key:
            existing_contact = contact_repo.get_by_email(dedup_key)
        elif dedup_key.startswith("name:"):
            # Extract components from key "name:xxx|phone:yyy"
            # Note: This lookup is specific to the MVP's string-based key logic
            try:
                parts = dedup_key.split("|")
                name = parts[0].replace("name:", "")
                phone = parts[1].replace("phone:", "")
                # This is a simplified search; in a real DB we'd use the exact phone normalization
                # logic within the SQL query or a dedicated dedup_key column.
                # For MVP, we'll iterate or use a specific repo method.
                existing_contact = contact_repo.get_by_phone_and_name(incoming.full_name, incoming.phone)
            except (IndexError, ValueError):
                pass

    now = datetime.utcnow()
    
    created = False
    if existing_contact:
        logger.info(f"Merging contact {existing_contact.id} with incoming from {incoming.provider_id}")
        if merge_contact_data(existing_contact, incoming):
            existing_contact.updated_at = now
            contact_repo.update(existing_contact)
        target_contact = existing_contact
    else:
        logger.info(f"Creating new contact for incoming from {incoming.provider_id}")
        new_contact = Contact(
            full_name=incoming.full_name,
            primary_email=incoming.primary_email,
            phone=incoming.phone,
            job_title=incoming.job_title,
            company_name=incoming.company_name,
            custom_fields=incoming.custom_fields,
            created_at=now,
            updated_at=now
        )
        target_contact = contact_repo.create(new_contact)
        created = True

    # Upsert SourceLink
    existing_link = link_repo.get_by_provider_external_id(
        incoming.provider_id, 
        incoming.external_id
    )
    
    if existing_link:
        existing_link.last_synced_at = now
        existing_link.contact_id = target_contact.id
        session.add(existing_link)
    else:
        new_link = SourceLink(
            provider_id=incoming.provider_id,
            external_id=incoming.external_id,
            contact_id=target_contact.id,
            last_synced_at=now
        )
        session.add(new_link)
    
    return target_contact, created

def run_integration_service(session: Session, integration_name: str) -> dict[str, Any]:
    """
    Orchestrates the ingestion from a specific integration.
    """
    # 1. Check if integration exists and is valid
    base_path = get_integrations_base_path()
    item = base_path / integration_name
    
    if not item.is_dir() or item.name.startswith("_") or not (item / "__init__.py").exists():
        raise ValueError(f"Unknown integration: {integration_name}")

    try:
        module_name = f"src.integrations.{integration_name}"
        module = importlib.import_module(module_name)
        fetch_fn = getattr(module, "fetch_contacts", None)
        if not fetch_fn or not callable(fetch_fn):
            raise ValueError(f"Unknown integration: {integration_name}")
    except (ImportError, AttributeError):
        raise ValueError(f"Unknown integration: {integration_name}")

    # 2. Run fetch and persist in a transaction
    fetched_count = 0
    created_count = 0
    updated_count = 0

    try:
        # Use a sub-transaction (nested) if session is already in one, 
        # but here we rely on the caller's session commit/rollback.
        contacts_iter = fetch_fn()
        
        for raw_item in contacts_iter:
            fetched_count += 1
            # Ensure the raw item is treated as IncomingContact
            if not isinstance(raw_item, IncomingContact):
                incoming = IncomingContact(**raw_item)
            else:
                incoming = raw_item
            
            _, created = persist_incoming_contact(session, incoming)
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Integration '{integration_name}' failed: {str(e)}", exc_info=True)
        raise RuntimeError(f"Integration failed: {str(e)}")

    return {
        "integration": integration_name,
        "fetched": fetched_count,
        "created": created_count,
        "updated": updated_count
    }