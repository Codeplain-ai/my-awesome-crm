import pytest
from src.integrations.salesforce.mapping import map_contact

def test_map_contact_full_payload():
    record = {
        "attributes": {"type": "Contact", "url": "/svc/123"},
        "Id": "SF-001",
        "Name": " Jane Doe ",
        "FirstName": "Jane",
        "LastName": "Doe",
        "Email": " JANE@example.com ",
        "Phone": "555-1234",
        "MobilePhone": "555-9999",
        "Title": "Engineer",
        "Account": {"Name": "Acme Corp", "attributes": {}},
        "Department": "IT",
        "Custom_Score__c": 42
    }
    
    result = map_contact(record)
    
    assert result["provider_id"] == "salesforce"
    assert result["external_id"] == "SF-001"
    assert result["full_name"] == "Jane Doe"
    assert result["primary_email"] == "jane@example.com"
    assert result["phone"] == "555-1234"
    assert result["job_title"] == "Engineer"
    assert result["company_name"] == "Acme Corp"
    # custom_fields should exclude consumed keys and attributes
    assert result["custom_fields"] == {"Department": "IT", "Custom_Score__c": 42}

def test_map_contact_name_derivation():
    # Case: Name is missing, use FirstName + LastName
    record = {
        "Id": "SF-002",
        "FirstName": "John",
        "LastName": "Smith"
    }
    result = map_contact(record)
    assert result["full_name"] == "John Smith"

    # Case: Name is empty, use parts
    record = {"Id": "SF-003", "Name": " ", "LastName": "Solo"}
    result = map_contact(record)
    assert result["full_name"] == "Solo"

def test_map_contact_phone_fallback():
    # Case: Phone missing, use Mobile
    record = {
        "Id": "SF-004",
        "MobilePhone": "123-456"
    }
    result = map_contact(record)
    assert result["phone"] == "123-456"

def test_map_contact_missing_fields():
    # Minimum possible valid SF record
    record = {"Id": "SF-MIN"}
    result = map_contact(record)
    
    assert result["external_id"] == "SF-MIN"
    assert result["full_name"] == ""
    assert result["primary_email"] is None
    assert result["phone"] is None
    assert result["company_name"] is None
    assert result["custom_fields"] == {}

def test_map_contact_email_normalization():
    record = {"Id": "SF-EM", "Email": " MIXed-Case@Domain.COM  "}
    result = map_contact(record)
    assert result["primary_email"] == "mixed-case@domain.com"