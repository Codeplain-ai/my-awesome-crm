from unittest.mock import MagicMock, patch
import pytest
from src.integrations.hubspot import fetch

@patch("src.integrations.hubspot.HubSpotClient")
def test_fetch_paginated(MockClient, monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token")
    
    # Mocking multi-page response via generator behavior
    mock_instance = MockClient.return_value
    mock_instance.list_contacts.return_value = iter([
        {"id": "c1", "properties": {"firstname": "A"}},
        {"id": "c2", "properties": {"firstname": "B"}}
    ])

    def get_stored(data_type):
        return []

    results = fetch(get_stored)

    assert len(results) == 2
    assert results[0]["data_type"] == "contact"
    assert results[0]["data"]["external_id"] == "c1"
    assert results[1]["data"]["external_id"] == "c2"

@patch("src.integrations.hubspot.HubSpotClient")
def test_fetch_skips_on_value_error(MockClient, monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token")
    
    mock_instance = MockClient.return_value
    mock_instance.list_contacts.return_value = [
        {"id": "good", "properties": {"firstname": "Good"}},
        {"id": "bad", "properties": {"firstname": "Bad"}}
    ]

    with patch("src.integrations.hubspot.map_contact") as mock_map:
        # First succeeds, second raises ValueError
        mock_map.side_effect = [
            {"external_id": "good"},
            ValueError("Invalid data")
        ]
        
        results = fetch(lambda dt: [])
        
        assert len(results) == 1
        assert results[0]["data"]["external_id"] == "good"

def test_fetch_missing_token(monkeypatch):
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="HUBSPOT_ACCESS_TOKEN"):
        fetch(lambda dt: [])
