from src.integrations.salesforce.mapping import map_contact_record

def test_map_contact_full_record():
    raw = {
        "attributes": {"type": "Contact", "url": "/services/data/v60.0/sobjects/Contact/003..."},
        "Id": "0035h00000XyZ",
        "Name": " John Doe ",
        "FirstName": "John",
        "LastName": "Doe",
        "Email": " JOHN.DOE@EXAMPLE.COM ",
        "Title": "Engineering Manager",
        "Account": {
            "attributes": {"type": "Account"},
            "Name": "Acme Corp"
        },
        "Department": "Product",
        "Custom_Field__c": "Special Value"
    }
    
    mapped = map_contact_record(raw)
    
    assert mapped["provider_id"] == "salesforce"
    assert mapped["external_id"] == "0035h00000XyZ"
    assert mapped["full_name"] == "John Doe"
    assert mapped["primary_email"] == "john.doe@example.com"
    assert mapped["job_title"] == "Engineering Manager"
    assert mapped["company_name"] == "Acme Corp"
    # Ensure consumed fields and metadata are NOT in custom_fields
    assert "Id" not in mapped["custom_fields"]
    assert "Account" not in mapped["custom_fields"]
    assert "attributes" not in mapped["custom_fields"]
    # Ensure extra fields ARE in custom_fields
    assert mapped["custom_fields"]["Department"] == "Product"
    assert mapped["custom_fields"]["Custom_Field__c"] == "Special Value"

def test_map_contact_name_derivation_fallback():
    # Case: Name is missing, use First/Last
    raw = {
        "Id": "1",
        "FirstName": "Jane",
        "LastName": "Smith"
    }
    mapped = map_contact_record(raw)
    assert mapped["full_name"] == "Jane Smith"

    # Case: Name and First missing, use Last
    raw = {
        "Id": "1",
        "LastName": "Bond"
    }
    mapped = map_contact_record(raw)
    assert mapped["full_name"] == "Bond"

    # Case: Everything missing
    raw = {"Id": "1"}
    mapped = map_contact_record(raw)
    assert mapped["full_name"] == ""

def test_map_contact_email_null_handling():
    raw = {"Id": "1", "Email": None}
    mapped = map_contact_record(raw)
    assert mapped["primary_email"] is None

def test_map_contact_account_null_handling():
    # Case: Account key is null
    raw = {"Id": "1", "Account": None}
    mapped = map_contact_record(raw)
    assert mapped["company_name"] is None

    # Case: Account key is missing
    raw = {"Id": "1"}
    mapped = map_contact_record(raw)
    assert mapped["company_name"] is None

    # Case: Account exists but Name is empty
    raw = {"Id": "1", "Account": {"Name": ""}}
    mapped = map_contact_record(raw)
    assert mapped["company_name"] is None

def test_map_contact_custom_fields_filtering():
    raw = {
        "Id": "123",
        "Name": "Name",
        "OtherField": "Keep Me"
    }
    mapped = map_contact_record(raw)
    # Consumed keys: Id, Name, FirstName, LastName, Email, Title, Account
    assert "Id" not in mapped["custom_fields"]
    assert mapped["custom_fields"]["OtherField"] == "Keep Me"

import pytest
from unittest.mock import patch, MagicMock
from src.integrations.salesforce import fetch

@patch("src.integrations.salesforce.client.httpx.post")
@patch("src.integrations.salesforce.client.httpx.get")
@patch.dict("os.environ", {
    "SALESFORCE_ENDPOINT": "https://test.salesforce.com",
    "SALESFORCE_CLIENT_ID": "id",
    "SALESFORCE_CLIENT_SECRET": "secret"
})
def test_fetch_paginated_success(mock_get, mock_post):
    # 1. Mock Authentication
    mock_auth_res = MagicMock()
    mock_auth_res.json.return_value = {
        "access_token": "fake_token",
        "instance_url": "https://instance.salesforce.com"
    }
    mock_auth_res.raise_for_status = MagicMock()
    mock_post.return_value = mock_auth_res

    # 2. Mock Multi-page Query
    # Page 1
    mock_res_p1 = MagicMock()
    mock_res_p1.json.return_value = {
        "totalSize": 3,
        "done": False,
        "nextRecordsUrl": "/services/data/v60.0/query/next-page-id",
        "records": [
            {"Id": "SF1", "Name": "User One", "Email": "u1@test.com"}
        ]
    }
    mock_res_p1.raise_for_status = MagicMock()
    
    # Page 2
    mock_res_p2 = MagicMock()
    mock_res_p2.json.return_value = {
        "totalSize": 3,
        "done": True,
        "records": [
            {"Id": "SF2", "Name": "User Two", "Email": "u2@test.com"},
            {"Id": "SF3", "Name": "User Three", "Email": "u3@test.com"}
        ]
    }
    mock_res_p2.raise_for_status = MagicMock()
    
    mock_get.side_effect = [mock_res_p1, mock_res_p2]

    # Execute
    results = fetch(get_stored=lambda x: [])

    # Assertions
    assert len(results) == 3
    assert results[0]["data"]["external_id"] == "SF1"
    assert results[1]["data"]["external_id"] == "SF2"
    assert results[2]["data"]["external_id"] == "SF3"
    assert all(r["data_type"] == "contact" for r in results)
    
    # Verify second call followed nextRecordsUrl
    assert mock_get.call_count == 2
    second_call_url = mock_get.call_args_list[1][0][0]
    assert "next-page-id" in second_call_url

@patch.dict("os.environ", {}, clear=True)
def test_fetch_missing_credentials_raises():
    with pytest.raises(RuntimeError) as excinfo:
        fetch(get_stored=lambda x: [])
    assert "SALESFORCE_ENDPOINT" in str(excinfo.value)


def test_integration_public_api():
    """
    Ensures the integration package exposes the required interface for discovery.
    """
    import src.integrations.salesforce as sf
    
    assert hasattr(sf, "fetch"), "Integration must export 'fetch'"
    assert callable(sf.fetch), "'fetch' must be a callable"
    assert hasattr(sf, "DATA_TYPE"), "Integration should export 'DATA_TYPE'"
    assert sf.DATA_TYPE == "contact"
    
    # Check __all__
    assert "fetch" in sf.__all__
    assert "DATA_TYPE" in sf.__all__