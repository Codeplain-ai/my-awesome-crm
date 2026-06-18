import src.integrations.copper as copper_plugin

def test_integration_exports_only_fetch_contacts():
    """
    Ensures the integration package follows the contract of exporting 
    only the required entry point.
    """
    # Check that fetch_contacts exists and is callable
    assert hasattr(copper_plugin, "fetch_contacts")
    assert callable(copper_plugin.fetch_contacts)
    
    # Check that __all__ is restricted to only fetch_contacts
    # This prevents accidental leakage of internal helpers into the host namespace
    assert copper_plugin.__all__ == ["fetch_contacts"]

def test_internal_helpers_not_in_all():
    """
    Ensures internal implementation details are not part of the public export list.
    """
    exported = copper_plugin.__all__
    assert "map_copper_contact" not in exported
    assert "get_credentials" not in exported
    assert "httpx" not in exported