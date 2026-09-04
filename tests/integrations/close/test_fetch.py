import pytest
from unittest.mock import MagicMock, patch
from src.integrations.close import fetch

@patch("src.integrations.close.client.httpx.get")
@patch.dict("os.environ", {"CLOSE_API_KEY": "sk_test_key"})
def test_fetch_pagination_logic(mock_get):
    """Verifies that fetch handles multiple pages of results."""
    # Page 1
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "data": [{"id": "c1", "name": "User 1"}],
        "has_more": True
    }
    
    # Page 2
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "data": [{"id": "c2", "name": "User 2"}],
        "has_more": False
    }
    
    mock_get.side_effect = [resp1, resp2]
    
    records = fetch(lambda dt: [])
    
    assert len(records) == 2
    assert records[0]["data"]["external_id"] == "c1"
    assert records[1]["data"]["external_id"] == "c2"
    assert mock_get.call_count == 2

@patch("src.integrations.close.client.httpx.get")
@patch.dict("os.environ", {"CLOSE_API_KEY": "sk_test_key"})
def test_fetch_skips_on_value_error(mock_get):
    """Verifies the skip-and-log policy when mapping raises ValueError."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [
            {"id": "valid", "name": "Valid"},
            {"id": "invalid", "name": "Fail"}
        ],
        "has_more": False
    }
    mock_get.return_value = resp

    with patch("src.integrations.close.map_contact") as mock_map:
        def side_effect(data):
            if data["id"] == "invalid":
                raise ValueError("Simulated mapping error")
            return {"external_id": data["id"]}
        
        mock_map.side_effect = side_effect
        records = fetch(lambda dt: [])
        
        assert len(records) == 1
        assert records[0]["data"]["external_id"] == "valid"

@patch.dict("os.environ", {"CLOSE_API_KEY": ""})
def test_fetch_missing_credentials_raises():
    with pytest.raises(RuntimeError) as exc:
        fetch(lambda dt: [])
    assert "CLOSE_API_KEY" in str(exc.value)