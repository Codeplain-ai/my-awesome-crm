import pytest
from src.integrations.sugarcrm.mapping import sugarcrm_contact_to_incoming

def test_mapping_full_name_provided():
    raw = {
        "id": "sugar-123",
        "full_name": "John Doe",
        "email1": "JOHN@example.com",
        "phone_work": "123-456",
        "title": "Manager",
        "account_name": "Acme Corp",
        "extra_field": "some-value"
    }
    result = sugarcrm_contact_to_incoming(raw)
    assert result["full_name"] == "John Doe"
    assert result["external_id"] == "sugar-123"
    assert result["primary_email"] == "john@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Manager"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"]["extra_field"] == "some-value"

def test_mapping_name_fallback():
    raw = {
        "id": "sugar-456",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone_mobile": "987-654"
    }
    result = sugarcrm_contact_to_incoming(raw)
    assert result["full_name"] == "Jane Smith"
    assert result["phone"] == "987-654"

def test_mapping_missing_id():
    with pytest.raises(ValueError, match="missing 'id'"):
        sugarcrm_contact_to_incoming({"full_name": "No ID"})

def test_mapping_missing_name():
    with pytest.raises(ValueError, match="missing a name"):
        sugarcrm_contact_to_incoming({"id": "id-only"})