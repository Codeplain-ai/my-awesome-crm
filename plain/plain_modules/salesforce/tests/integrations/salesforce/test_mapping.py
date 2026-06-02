import pytest
from src.integrations.salesforce.mapping import salesforce_contact_to_incoming

def test_mapping_full_payload():
    sf_data = {
        "attributes": {"type": "Contact", "url": "/003P000001AmXYZ"},
        "Id": "003P000001AmXYZ",
        "Name": "John Doe",
        "Email": " JOHN.doe@Example.com ",
        "Phone": "+1-555-010-999",
        "Title": "Chief Officer",
        "Account": {"Name": "Acme Corp"},
        "Custom_Score__c": 42,
        "Department": "Engineering"
    }
    
    result = salesforce_contact_to_incoming(sf_data)
    
    assert result["provider_id"] == "salesforce"
    assert result["external_id"] == "003P000001AmXYZ"
    assert result["full_name"] == "John Doe"
    assert result["primary_email"] == "john.doe@example.com"
    assert result["phone"] == "+1-555-010-999"
    assert result["job_title"] == "Chief Officer"
    assert result["company_name"] == "Acme Corp"
    assert result["custom_fields"] == {"Custom_Score__c": 42, "Department": "Engineering"}

def test_mapping_name_fallback():
    sf_data = {
        "Id": "003P001",
        "FirstName": " Jane ",
        "LastName": "Smith ",
        "Email": "jane@smith.com"
    }
    
    result = salesforce_contact_to_incoming(sf_data)
    assert result["full_name"] == "Jane Smith"

def test_mapping_missing_id_raises():
    sf_data = {"Name": "No ID"}
    with pytest.raises(ValueError, match="missing required field: Id"):
        salesforce_contact_to_incoming(sf_data)

def test_mapping_missing_name_raises():
    sf_data = {"Id": "003P002", "Email": "anon@example.com"}
    with pytest.raises(ValueError, match="no valid Name, FirstName, or LastName"):
        salesforce_contact_to_incoming(sf_data)