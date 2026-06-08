import pytest
from unittest.mock import patch, MagicMock
from src.integrations.salesforce.client import fetch_contacts
from src.integrations.salesforce import fetch_contacts as exported_fetch_contacts

def test_integration_exports_fetch_contacts():
    """Verify the discovery contract: __init__ must export fetch_contacts."""
    assert exported_fetch_contacts is fetch_contacts

@patch("src.integrations.salesforce.client._acquire_token")
@patch("src.integrations.salesforce.client._get_json")
@patch.dict("os.environ", {
    "SALESFORCE_ENDPOINT": "https://test.salesforce.com",
    "SALESFORCE_CLIENT_ID": "id",
    "SALESFORCE_CLIENT_SECRET": "secret"
})
def test_fetch_contacts_pagination_and_skip(mock_get_json, mock_auth):
    # Mock Auth
    mock_auth.return_value = ("fake_token", "https://instance.salesforce.com")

    # Mock Page 1 (1 good, 1 bad)
    page1 = {
        "done": False,
        "nextRecordsUrl": "/next-page",
        "records": [
            {"Id": "1", "Name": "Good One"},
            {"Id": "2"} # Missing name/required fields, will raise ValueError in mapping
        ]
    }
    # Mock Page 2 (1 good)
    page2 = {
        "done": True,
        "records": [
            {"Id": "3", "Name": "Good Two"}
        ]
    }

    mock_get_json.side_effect = [page1, page2]

    results = list(fetch_contacts())

    assert len(results) == 2
    assert results[0]["external_id"] == "1"
    assert results[1]["external_id"] == "3"
    # Verify calls
    assert mock_get_json.call_count == 2
    # First call should have params
    args1, kwargs1 = mock_get_json.call_args_list[0]
    # Check positional args (index 2) or keyword args
    params = args1[2] if len(args1) > 2 else kwargs1.get("params", {})
    assert "q" in params
    # Second call should use nextRecordsUrl joined with instance_url
    args2, _ = mock_get_json.call_args_list[1]
    assert args2[0] == "https://instance.salesforce.com/next-page"

@patch.dict("os.environ", {}, clear=True)
def test_fetch_contacts_missing_creds():
    with pytest.raises(RuntimeError, match="Missing Salesforce credentials"):
        fetch_contacts()