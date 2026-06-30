import src.integrations.zendesk_sell as zendesk_sell

def test_public_api_exposure():
    """
    Verify that the integration correctly exposes the required interface
    for the host's discovery mechanism.
    """
    # Must expose the fetch callable
    assert hasattr(zendesk_sell, "fetch")
    assert callable(zendesk_sell.fetch)
    
    # Must expose the DATA_TYPE attribute
    assert hasattr(zendesk_sell, "DATA_TYPE")
    assert zendesk_sell.DATA_TYPE == "contact"
    
    # Verify __all__ is correctly defined
    assert set(zendesk_sell.__all__) == {"fetch", "DATA_TYPE"}

def test_internal_encapsulation():
    """
    Verify that while internal modules are importable, they aren't part
    of the explicitly declared public API.
    """
    # Internal helpers should not be in __all__
    assert "ZendeskSellClient" not in zendesk_sell.__all__
    assert "map_contact" not in zendesk_sell.__all__