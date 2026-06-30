import src.integrations.nimble as nimble

def test_integration_exports_required_interface():
    """
    Verifies that the integration package exposes the interface expected 
    by the host's discovery logic in ingest.py.
    """
    # Check for fetch callable
    assert hasattr(nimble, "fetch")
    assert callable(nimble.fetch)
    
    # Check for DATA_TYPE attribute
    assert hasattr(nimble, "DATA_TYPE")
    assert nimble.DATA_TYPE == "contact"

def test_public_api_definition():
    """
    Verifies that the package explicitly defines its public API via __all__.
    """
    assert hasattr(nimble, "__all__")
    assert "fetch" in nimble.__all__
    assert "DATA_TYPE" in nimble.__all__
    
    # Internal modules should not be in __all__
    assert "NimbleClient" not in nimble.__all__
    assert "map_contact" not in nimble.__all__