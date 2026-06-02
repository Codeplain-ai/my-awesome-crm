import pytest
from src.integrations.hubspot.mapping import hubspot_contact_to_incoming

def test_mapping_full_payload():
    payload = {
        "id": "123",
        "properties": {
            "firstname": "John",
            "lastname": "Doe",
            "email": "JOHN.DOE@example.com",
            "phone": "555-1234",
            "jobtitle": "Engineer",
            "company": "ACME Corp",
            "industry": "Tech",
            "favourite_color": "blue"
        }
    }
    result = hubspot_contact_to_incoming(payload)
    
    assert result["provider_id"] == "hubspot"
    assert result["external_id"] == "123"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "ACME Corp"
    assert result["custom_fields"] == {"industry": "Tech", "favourite_color": "blue"}

def test_mapping_name_fallback_to_email():
    payload = {
        "id": "456",
        "properties": {
            "email": "janedoe@provider.com",
            "firstname": "",
            "lastname": None
        }
    }
    result = hubspot_contact_to_incoming(payload)
    assert result["full_name"] == "janedoe"

def test_mapping_missing_id_raises():
    payload = {"properties": {"firstname": "NoID"}}
    with pytest.raises(ValueError, match="missing the required 'id' field"):
        hubspot_contact_to_incoming(payload)

def test_mapping_no_name_or_email_raises():
    payload = {
        "id": "789",
        "properties": {
            "firstname": " ",
            "lastname": ""
        }
    }
    with pytest.raises(ValueError, match="Could not determine a non-empty full_name"):
        hubspot_contact_to_incoming(payload)