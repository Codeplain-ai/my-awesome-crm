import pytest
from src.integrations.salesforce.mapping import map_contact

def test_map_contact_full_payload():
    """Tests mapping with all fields populated."""
    raw = {
        "attributes": {"type": "Contact", "url": "/svc/data/v60.0/sobjects/Contact/003"},
        "Id": "0031",
        "Name": " Jane Doe ",
        "FirstName": "Jane",
        "LastName": "Doe",
        "Email": " JANE.doe@EXAMPLE.com ",
        "Phone": "555-1234",
        "MobilePhone": "555-6789",
        "Title": "Engineer",
        "Account": {
            "attributes": {"type": "Account", "url": "/svc/001"},
            "Name": "Acme Corp"
        },
        "Department": "R&D",
        "LeadSource": "Web"
    }
    
    mapped = map_contact(raw)
    
    assert mapped["provider_id"] == "salesforce"
    assert mapped["external_id"] == "0031"
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane.doe@example.com"
    assert mapped["phone"] == "555-1234"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"] == {"Department": "R&D", "LeadSource": "Web"}

def test_map_contact_name_derivation_fallback():
    """Tests full_name derivation when 'Name' is missing."""
    raw = {
        "Id": "0032",
        "FirstName": "John",
        "LastName": "Smith"
    }
    mapped = map_contact(raw)
    assert mapped["full_name"] == "John Smith"

def test_map_contact_name_derivation_empty():
    """Tests full_name derivation when all name components are missing."""
    raw = {"Id": "0033"}
    mapped = map_contact(raw)
    assert mapped["full_name"] == ""

def test_map_contact_phone_fallback():
    """Tests phone falls back to MobilePhone if Phone is missing."""
    raw = {
        "Id": "0034",
        "MobilePhone": " 555-9999 "
    }
    mapped = map_contact(raw)
    assert mapped["phone"] == "555-9999"

def test_map_contact_email_none():
    """Tests primary_email maps to None when missing or empty."""
    assert map_contact({"Id": "1"})["primary_email"] is None
    assert map_contact({"Id": "1", "Email": " "})["primary_email"] is None

def test_map_contact_company_name_null_account():
    """Tests company_name is None when Account object is null."""
    raw = {
        "Id": "0035",
        "Account": None
    }
    mapped = map_contact(raw)
    assert mapped["company_name"] is None

def test_map_contact_custom_fields_exclusion():
    """Tests that attributes and consumed fields are excluded from custom_fields."""
    raw = {
        "Id": "0036",
        "Name": "Name",
        "attributes": {"some": "meta"},
        "Account": {"Name": "Acc", "attributes": {}},
        "SecretField": "Hidden"
    }
    mapped = map_contact(raw)
    # custom_fields should ONLY contain 'SecretField'
    assert mapped["custom_fields"] == {"SecretField": "Hidden"}

import os
from unittest.mock import patch, MagicMock
from src.integrations.salesforce import fetch

def test_fetch_missing_credentials():
    """Tests that fetch raises RuntimeError if env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as exc:
            fetch(lambda _: [])
        assert "SALESFORCE_ENDPOINT" in str(exc.value)

@patch("httpx.Client")
def test_fetch_success_with_pagination(mock_client_class):
    """Tests full fetch flow including auth and 2-page pagination."""
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Mock environment
    env = {
        "SALESFORCE_ENDPOINT": "https://login.salesforce.com",
        "SALESFORCE_CLIENT_ID": "id",
        "SALESFORCE_CLIENT_SECRET": "secret"
    }
    
    # Define response sequence
    # 1. Auth Response
    res_auth = MagicMock()
    res_auth.status_code = 200
    res_auth.json.return_value = {
        "access_token": "token123",
        "instance_url": "https://na1.salesforce.com"
    }
    
    # 2. First Page Response (done=False)
    res_p1 = MagicMock()
    res_p1.status_code = 200
    res_p1.json.return_value = {
        "totalSize": 2,
        "done": False,
        "nextRecordsUrl": "/services/data/v60.0/query/next-page-id",
        "records": [{"Id": "c1", "LastName": "One"}]
    }
    
    # 3. Second Page Response (done=True)
    res_p2 = MagicMock()
    res_p2.status_code = 200
    res_p2.json.return_value = {
        "totalSize": 2,
        "done": True,
        "records": [{"Id": "c2", "LastName": "Two"}]
    }
    
    mock_client.post.return_value = res_auth
    mock_client.get.side_effect = [res_p1, res_p2]
    
    with patch.dict(os.environ, env):
        results = fetch(lambda _: [])
    
    assert len(results) == 2
    assert results[0]["external_id"] == "c1"
    assert results[1]["external_id"] == "c2"
    
    # Verify auth was called
    mock_client.post.assert_called_once()
    # Verify query was called twice (initial + next)
    assert mock_client.get.call_count == 2