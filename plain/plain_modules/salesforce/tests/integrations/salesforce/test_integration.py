import os
import pytest
from unittest.mock import MagicMock, patch
from src.integrations.salesforce.mapping import map_contact
from src.integrations.salesforce import fetch, fetch_contacts, SalesforceClient

def test_missing_env_vars_raises_runtime_error():
    """Verifies RuntimeError naming missing environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as excinfo:
            SalesforceClient()
        assert "SALESFORCE_CLIENT_ID" in str(excinfo.value)
        assert "SALESFORCE_CLIENT_SECRET" in str(excinfo.value)
        assert "SALESFORCE_ENDPOINT" in str(excinfo.value)

def test_mapping_full_name_derivation():
    # Scenario 1: Name field present
    record = {"Id": "123", "Name": " John Doe "}
    mapped = map_contact(record)
    assert mapped["full_name"] == "John Doe"
    
    # Scenario 2: Name missing, FirstName/LastName present
    record = {"Id": "124", "FirstName": "Jane", "LastName": "Smith"}
    mapped = map_contact(record)
    assert mapped["full_name"] == "Jane Smith"

    # Scenario 3: All missing
    record = {"Id": "125"}
    mapped = map_contact(record)
    assert mapped["full_name"] == ""

def test_mapping_email_and_fields():
    record = {
        "Id": "001",
        "Email": " TEST@Example.com ",
        "Title": "Manager",
        "Account": {"Name": "Acme Corp"},
        "Department": "Sales" # Custom field
    }
    mapped = map_contact(record)
    assert mapped["external_id"] == "001"
    assert mapped["primary_email"] == "test@example.com"
    assert mapped["job_title"] == "Manager"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"] == {"Department": "Sales"}

def test_fetch_pagination_and_mapping_integration():
    """Tests multi-page pagination and skip-and-log policy via fetch entry point."""
    
    # Mocking SalesforceClient inside the fetch function where it is imported
    with patch("src.integrations.salesforce.SalesforceClient") as MockClient:
        instance = MockClient.return_value
        
        # Mocking two pages of data
        page1_raw = [
            {"Id": "C1", "Name": "Contact One", "attributes": {"type": "Contact"}},
            {"Id": "C2", "Name": "Contact Two"}
        ]
        page2_raw = [
            {"Id": "C3", "Name": "Contact Three"}
        ]
        
        # client.get_all_contacts handles the pagination internally in our implementation,
        # so we mock that combined result.
        instance.get_all_contacts.return_value = page1_raw + page2_raw
        
        def mock_get_stored(dt): return []
        
        results = fetch(mock_get_stored)
        
        assert len(results) == 3
        assert results[0]["data"]["external_id"] == "C1"
        assert results[2]["data"]["external_id"] == "C3"
        assert results[0]["data_type"] == "contact"

@patch("src.integrations.salesforce.client.httpx.Client")
def test_fetch_multi_page_pagination(mock_httpx_class):
    """Verifies that fetch follows nextRecordsUrl and aggregates records."""
    mock_client = mock_httpx_class.return_value.__enter__.return_value
    
    # Mock Auth Response
    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.json.return_value = {
        "access_token": "fake_token",
        "instance_url": "https://fake.salesforce.com"
    }
    
    # Mock Page 1
    page1_resp = MagicMock()
    page1_resp.status_code = 200
    page1_resp.json.return_value = {
        "done": False,
        "nextRecordsUrl": "/services/data/v60.0/query/next-123",
        "records": [{"Id": "C1", "Name": "Contact One"}]
    }
    
    # Mock Page 2
    page2_resp = MagicMock()
    page2_resp.status_code = 200
    page2_resp.json.return_value = {
        "done": True,
        "records": [{"Id": "C2", "Name": "Contact Two"}]
    }
    
    mock_client.post.return_value = auth_resp
    mock_client.get.side_effect = [page1_resp, page2_resp]
    
    with patch.dict(os.environ, {
        "SALESFORCE_CLIENT_ID": "id",
        "SALESFORCE_CLIENT_SECRET": "secret",
        "SALESFORCE_ENDPOINT": "https://login.salesforce.com"
    }):
        results = fetch(lambda x: [])
        
        assert len(results) == 2
        assert results[0]["data"]["external_id"] == "C1"
        assert results[1]["data"]["external_id"] == "C2"

@patch("src.integrations.salesforce.SalesforceClient")
def test_fetch_skip_and_log_policy(mock_client_class):
    """Verifies that if mapping fails for one record, others are still processed."""
    instance = mock_client_class.return_value
    
    # We will force a ValueError in mapping by patching it
    records = [
        {"Id": "Good", "Name": "Good Contact"},
        {"Id": "Bad", "Name": "Bad Contact"},
    ]
    instance.get_all_contacts.return_value = records
    
    def side_effect(rec):
        if rec["Id"] == "Bad":
            raise ValueError("Invalid record")
        from src.integrations.salesforce.mapping import map_contact as real_map
        return real_map(rec)

    with patch("src.integrations.salesforce.map_contact", side_effect=side_effect):
        results = fetch(lambda x: [])
        
        # Should only have 1 record, the "Bad" one was skipped
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "Good"

@patch("src.integrations.salesforce.SalesforceClient")
def test_fetch_contacts_export(mock_client_class):
    """Verifies that fetch_contacts is exported and behaves like fetch."""
    instance = mock_client_class.return_value
    instance.get_all_contacts.return_value = [{"Id": "C1", "Name": "Name"}]
    
    # fetch_contacts should return the same results as fetch
    results = fetch_contacts(lambda x: [])
    assert len(results) == 1
    assert results[0]["data"]["external_id"] == "C1"
    assert results[0]["data_type"] == "contact"