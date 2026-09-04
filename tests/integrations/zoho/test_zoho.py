import pytest
from unittest.mock import MagicMock, patch
from src.integrations.zoho.mapping import map_zoho_contact
from src.integrations.zoho import fetch

def test_mapping_full_name_derivation():
    """Verifies the four-step full_name derivation rule."""
    # Scenario 1: Full_Name present
    res = map_zoho_contact({"id": "1", "Full_Name": " Alice Smith "})
    assert res["full_name"] == "Alice Smith"
    
    # Scenario 2: First + Last
    res = map_zoho_contact({"id": "2", "First_Name": "Bob", "Last_Name": "Jones"})
    assert res["full_name"] == "Bob Jones"
    
    # Scenario 3: Email as fallback
    res = map_zoho_contact({"id": "3", "Email": "charlie@test.com"})
    assert res["full_name"] == "charlie@test.com"
    
    # Scenario 4: Empty fallback
    res = map_zoho_contact({"id": "4"})
    assert res["full_name"] == ""

def test_mapping_company_name():
    """Verifies the three-shape company_name derivation from Account_Name."""
    # Object shape
    res = map_zoho_contact({"id": "1", "Account_Name": {"name": "Acme Corp", "id": "acc1"}})
    assert res["company_name"] == "Acme Corp"
    
    # String shape
    res = map_zoho_contact({"id": "2", "Account_Name": " Globex "})
    assert res["company_name"] == "Globex"
    
    # Null shape
    res = map_zoho_contact({"id": "3", "Account_Name": None})
    assert res["company_name"] is None

def test_custom_fields_exclusion():
    """Verifies that consumed keys and system metadata are excluded from custom_fields."""
    raw = {
        "id": "123",
        "Email": "test@test.com",
        "Department": "Engineering",
        "$approved": True,
        "Owner": {"name": "Manager"}
    }
    res = map_zoho_contact(raw)
    # Department is not in consumed keys
    assert res["custom_fields"] == {"Department": "Engineering"}
    # System metadata ($ prefix) excluded
    assert "$approved" not in res["custom_fields"]
    # Owner lookup excluded
    assert "Owner" not in res["custom_fields"]

@patch("src.integrations.zoho.client.ZohoClient.authenticate")
@patch("src.integrations.zoho.client.ZohoClient.list_contacts")
def test_fetch_orchestration(mock_list, mock_auth):
    """Verifies fetch(get_stored) calls auth, fetches data, and returns mapped records."""
    mock_list.return_value = [
        {"id": "z1", "Full_Name": "User One"},
        {"id": "z2", "Full_Name": "User Two"}
    ]
    
    get_stored = MagicMock(return_value=[])
    results = fetch(get_stored)
    
    assert len(results) == 2
    assert results[0]["data_type"] == "contact"
    assert results[0]["data"]["external_id"] == "z1"
    assert results[1]["data"]["full_name"] == "User Two"

@patch("httpx.get")
@patch("httpx.post")
def test_client_pagination(mock_post, mock_get):
    """Verifies that the client fetches multiple pages until more_records is False."""
    # Mock Token
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "fake_token"})
    
    # Mock two pages of data
    page1 = {
        "data": [{"id": "p1"}],
        "info": {"more_records": True}
    }
    page2 = {
        "data": [{"id": "p2"}],
        "info": {"more_records": False}
    }
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: page1),
        MagicMock(status_code=200, json=lambda: page2)
    ]
    
    from src.integrations.zoho.client import ZohoClient
    with patch.dict("os.environ", {
        "ZOHO_ACCOUNTS_HOST": "https://accounts.zoho.com",
        "ZOHO_API_HOST": "https://www.zohoapis.com",
        "ZOHO_CLIENT_ID": "cid",
        "ZOHO_CLIENT_SECRET": "cs",
        "ZOHO_REFRESH_TOKEN": "rt"
    }):
        client = ZohoClient()
        client.authenticate()
        records = client.list_contacts()
        
    assert len(records) == 2
    assert records[0]["id"] == "p1"
    assert records[1]["id"] == "p2"
    assert mock_get.call_count == 2

def test_client_missing_env_vars():
    """Verifies that authentication fails when environment variables are missing."""
    from src.integrations.zoho.client import ZohoClient
    with patch.dict("os.environ", {}, clear=True):
        client = ZohoClient()
        with pytest.raises(RuntimeError) as excinfo:
            client.authenticate()
        assert "Missing required environment variables" in str(excinfo.value)
        assert "ZOHO_CLIENT_ID" in str(excinfo.value)

@patch("httpx.get")
def test_client_handle_204_no_content(mock_get):
    """Verifies that HTTP 204 is handled as an empty record set."""
    from src.integrations.zoho.client import ZohoClient
    mock_get.return_value = MagicMock(status_code=204)
    
    with patch.dict("os.environ", {
        "ZOHO_ACCOUNTS_HOST": "https://accounts.zoho.com",
        "ZOHO_API_HOST": "https://www.zohoapis.com",
        "ZOHO_CLIENT_ID": "cid",
        "ZOHO_CLIENT_SECRET": "cs",
        "ZOHO_REFRESH_TOKEN": "rt"
    }):
        client = ZohoClient()
        client.access_token = "valid"
        records = client.list_contacts()
        
    assert records == []

def test_fetch_skip_and_log_policy():
    """Verifies that a ValueError in mapping skips the record and continues."""
    from src.integrations.zoho import fetch
    
    # Create a record that will trigger a ValueError if we force it
    # We'll mock map_zoho_contact inside fetch
    with patch("src.integrations.zoho.client.ZohoClient.authenticate"), \
         patch("src.integrations.zoho.client.ZohoClient.list_contacts") as mock_list, \
         patch("src.integrations.zoho.map_zoho_contact") as mock_map:
        
        mock_list.return_value = [{"id": "bad"}, {"id": "good"}]
        mock_map.side_effect = [ValueError("Simulated mapping error"), {"external_id": "good"}]
        
        get_stored = MagicMock(return_value=[])
        results = fetch(get_stored)
        
        # 'bad' record skipped, 'good' record returned
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "good"