import pytest
from src.models.schemas import IncomingContact
from src.services.dedup import compute_dedup_key, merge_contact_data
from src.models.db import Contact

def test_compute_dedup_key_email():
    ic = IncomingContact(
        provider_id="test", 
        external_id="1", 
        full_name="User", 
        primary_email="  BOB@Example.Com  "
    )
    assert compute_dedup_key(ic) == "bob@example.com"

def test_compute_dedup_key_fallback():
    ic = IncomingContact(
        provider_id="test", 
        external_id="1", 
        full_name="John Doe", 
        phone="+1 (555) 000-1234"
    )
    assert compute_dedup_key(ic) == "name:john doe|phone:15550001234"

def test_compute_dedup_key_insufficient_data():
    ic = IncomingContact(provider_id="test", external_id="1", full_name="No Phone")
    assert compute_dedup_key(ic) is None

def test_merge_contact_data():
    existing = Contact(full_name="John", job_title=None, custom_fields={"a": 1})
    incoming = IncomingContact(
        provider_id="p1", 
        external_id="e1", 
        full_name="John Doe", 
        job_title="CEO",
        custom_fields={"a": 2, "b": 3}
    )
    
    changed = merge_contact_data(existing, incoming)
    
    assert changed is True
    # full_name kept existing because "John" is non-empty
    assert existing.full_name == "John"
    # job_title filled because existing was None
    assert existing.job_title == "CEO"
    # custom_fields shallow merged
    assert existing.custom_fields == {"a": 2, "b": 3}