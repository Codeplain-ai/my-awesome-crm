import src.integrations.zoho as zoho

def test_integration_exports_only_fetch_contacts():
    """
    Evaluates :codeplain::AdditionalFunctionality: to ensure only 
    fetch_contacts is exported to the host.
    """
    # Check __all__
    assert hasattr(zoho, "__all__"), "Integration should define __all__"
    assert zoho.__all__ == ["fetch_contacts"], "Integration must export only 'fetch_contacts'"
    
    # Check actual presence
    assert hasattr(zoho, "fetch_contacts"), "fetch_contacts must be present"
    assert callable(zoho.fetch_contacts), "fetch_contacts must be a callable"
    
    # Verify non-exported helpers are not in the public interface via __all__
    # Even if they are imported in __init__.py for internal use, they should not be in __all__
    assert "map_zoho_contact" not in zoho.__all__
    assert "get_credentials" not in zoho.__all__