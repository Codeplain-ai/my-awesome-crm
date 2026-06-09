import pytest
from src.integrations.dynamics.mapping import dynamics_contact_to_incoming

def test_mapping_full_record():
    payload = {
        "contactid": "uuid-123",
        "fullname": " John Doe  ",
        "emailaddress1": "JOHN@example.com",
        "telephone1": "123-456",
        "jobtitle": "Software Engineer",
        "department": "Engineering",
        "parentcustomerid_account": {"name": "Acme Corp"},
        "@odata.etag": "12345"
    }
    result = dynamics_contact_to_incoming(payload)
    
    assert result["provider_id"] == "dynamics"
    assert result["external_id"] == "uuid-123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john@example.com"
    assert result["phone"] == "123-456"
    assert result["job_title"] == "Software Engineer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"department": "Engineering"}

def test_mapping_name_fallback():
    payload = {
        "contactid": "uuid-456",
        "firstname": "Jane",
        "lastname": "Smith",
    }
    result = dynamics_contact_to_incoming(payload)
    assert result["full_name"] == "Jane Smith"

def test_mapping_invalid_email_logs_and_returns_none(caplog):
    payload = {
        "contactid": "uuid-789",
        "fullname": "Bad Email User",
        "emailaddress1": "not-an-email"
    }
    result = dynamics_contact_to_incoming(payload)
    assert result["primary_email"] is None
    assert "invalid emailaddress1" in caplog.text
    assert "uuid-789" in caplog.text

def test_mapping_missing_id_raises():
    payload = {"fullname": "No ID"}
    with pytest.raises(ValueError, match="missing mandatory 'contactid'"):
        dynamics_contact_to_incoming(payload)

def test_mapping_missing_name_raises():
    payload = {"contactid": "uuid-000"}
    with pytest.raises(ValueError, match="has no valid name fields"):
        dynamics_contact_to_incoming(payload)

def test_mapping_phone_fallback():
    payload = {
        "contactid": "uuid-1",
        "fullname": "Phone Test",
        "mobilephone": "999-999"
    }
    result = dynamics_contact_to_incoming(payload)
    assert result["phone"] == "999-999"

def test_mapping_custom_fields_filter_metadata():
    payload = {
        "contactid": "id",
        "fullname": "Name",
        "custom_key": "value",
        "@odata.context": "metadata-url"
    }
    result = dynamics_contact_to_incoming(payload)
    assert "custom_key" in result["custom_fields"]
    assert "@odata.context" not in result["custom_fields"]