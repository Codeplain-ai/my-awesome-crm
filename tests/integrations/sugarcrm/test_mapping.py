import pytest
from src.integrations.sugarcrm.mapping import sugarcrm_contact_to_incoming

def test_mapping_full_data():
    raw = {
        "id": "sugar-123",
        "full_name": "John Doe",
        "email1": "JOHN@example.com",
        "phone_work": "123-456",
        "title": "Manager",
        "account_name": "Acme Corp",
        "department": "Engineering"
    }
    result = sugarcrm_contact_to_incoming(raw)
    assert result["provider_id"] == "sugarcrm"
    assert result["external_id"] == "sugar-123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Manager"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"]["department"] == "Engineering"

def test_mapping_name_concatenation_fallback():
    raw = {
        "id": "sugar-456",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone_mobile": "987-654"
    }
    result = sugarcrm_contact_to_incoming(raw)
    assert result["full_name"] == "Jane Smith"
    assert result["phone"] == "987-654"

def test_mapping_missing_required_id():
    with pytest.raises(ValueError, match="missing 'id'"):
        sugarcrm_contact_to_incoming({"full_name": "No ID"})

def test_mapping_missing_required_name():
    with pytest.raises(ValueError, match="missing a name"):
        sugarcrm_contact_to_incoming({"id": "id-only"})

def test_mapping_empty_strings_handled():
    raw = {
        "id": "1",
        "full_name": "Name",
        "email1": " ",
        "phone_work": "",
        "phone_mobile": None
    }
    result = sugarcrm_contact_to_incoming(raw)
    assert result["primary_email"] is None
    assert result["phone"] is None