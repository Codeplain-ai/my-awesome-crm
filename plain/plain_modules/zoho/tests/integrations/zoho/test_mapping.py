import pytest
from src.integrations.zoho.mapping import zoho_contact_to_incoming

def test_mapping_basic():
    raw = {
        "id": "zoho_123",
        "Full_Name": "Alice Smith",
        "Email": "ALICE@example.com ",
        "Phone": "+123456",
        "Title": "Engineer",
        "Account_Name": {"id": "acc_1", "name": "Tech Corp"},
        "Favorite_Color": "Blue"
    }
    incoming = zoho_contact_to_incoming(raw)
    
    assert incoming["provider_id"] == "zoho"
    assert incoming["external_id"] == "zoho_123"
    assert incoming["full_name"] == "Alice Smith"
    assert incoming["primary_email"] == "alice@example.com"
    assert incoming["phone"] == "+123456"
    assert incoming["job_title"] == "Engineer"
    assert incoming["company_name"] == "Tech Corp"
    assert incoming["custom_fields"] == {"Favorite_Color": "Blue"}

def test_mapping_name_fallback():
    raw = {
        "id": "zoho_456",
        "First_Name": " Bob ",
        "Last_Name": "Builder ",
        "Email": "bob@build.it"
    }
    incoming = zoho_contact_to_incoming(raw)
    assert incoming["full_name"] == "Bob Builder"

def test_mapping_account_string():
    raw = {
        "id": "zoho_789",
        "Full_Name": "Charlie",
        "Account_Name": "Individual Contributor"
    }
    incoming = zoho_contact_to_incoming(raw)
    assert incoming["company_name"] == "Individual Contributor"

def test_mapping_missing_id():
    with pytest.raises(ValueError, match="missing the required 'id'"):
        zoho_contact_to_incoming({"Full_Name": "No ID"})

def test_mapping_missing_name():
    with pytest.raises(ValueError, match="missing a valid name"):
        zoho_contact_to_incoming({"id": "123"})