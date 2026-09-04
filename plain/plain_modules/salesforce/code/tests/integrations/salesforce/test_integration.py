import pytest
from unittest.mock import MagicMock, patch
from src.integrations.salesforce.mapping import map_contact_record
from src.integrations.salesforce import fetch

def test_mapping_basic():
    """Verifies standard mapping with all fields present."""
    record = {
        "attributes": {"type": "Contact", "url": "..."},
        "Id": "003xxxx",
        "Name": " Jane Doe ",
        "FirstName": "Jane",
        "LastName": "Doe",
        "Email": "JANE@example.com",
        "Title": "Engineer",
        "Account": {"Name": "Acme Corp"},
        "Department": "R&D"
    }
    mapped = map_contact_record(record)
    assert mapped["provider_id"] == "salesforce"
    assert mapped["external_id"] == "003xxxx"
    assert mapped["full_name"] == "Jane Doe"
    assert mapped["primary_email"] == "jane@example.com"
    assert mapped["job_title"] == "Engineer"
    assert mapped["company_name"] == "Acme Corp"
    assert mapped["custom_fields"] == {"Department": "R&D"}

def test_mapping_name_derivation():
    """Verifies fallback name joining."""
    record = {
        "Id": "1",
        "FirstName": "Bob",
        "LastName": "Smith",
        "Email": None
    }
    mapped = map_contact_record(record)
    assert mapped["full_name"] == "Bob Smith"
    
    record_no_first = {"Id": "2", "LastName": "Single"}
    assert map_contact_record(record_no_first)["full_name"] == "Single"
    
    record_empty = {"Id": "3"}
    assert map_contact_record(record_empty)["full_name"] == ""

def test_mapping_missing_optional_data():
    """Verifies robustness against null/missing values."""
    record = {"Id": "123", "LastName": "Anonymous"}
    mapped = map_contact_record(record)
    assert mapped["primary_email"] is None
    assert mapped["job_title"] is None
    assert mapped["company_name"] is None

@patch("src.integrations.salesforce.client.httpx.post")
@patch("src.integrations.salesforce.client.httpx.get")
def test_fetch_pagination(mock_get, mock_post):
    """Verifies fetch handles multi-page pagination via the client."""
    # 1. Mock Auth
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "tk_123", "instance_url": "https://inst.sf.com"}
    )
    
    # 2. Mock Pagination (Page 1 then Page 2)
    mock_get.side_effect = [
        MagicMock(
            status_code=200,
            json=lambda: {
                "totalSize": 2,
                "done": False,
                "nextRecordsUrl": "/next/page",
                "records": [{"Id": "rec1", "LastName": "One"}]
            }
        ),
        MagicMock(
            status_code=200,
            json=lambda: {
                "totalSize": 2,
                "done": True,
                "records": [{"Id": "rec2", "LastName": "Two"}]
            }
        )
    ]
    
    with patch.dict("os.environ", {
        "SALESFORCE_ENDPOINT": "https://login.sf.com",
        "SALESFORCE_CLIENT_ID": "cid",
        "SALESFORCE_CLIENT_SECRET": "csec"
    }):
        results = fetch(lambda x: [])
        assert len(results) == 2
        assert results[0]["data"]["external_id"] == "rec1"
        assert results[1]["data"]["external_id"] == "rec2"

def test_fetch_missing_credentials():
    """Verifies fetch raises if credentials are not provided."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError) as exc:
            fetch(lambda x: [])
        assert "Missing required Salesforce credentials" in str(exc.value)
        assert "SALESFORCE_ENDPOINT" in str(exc.value)