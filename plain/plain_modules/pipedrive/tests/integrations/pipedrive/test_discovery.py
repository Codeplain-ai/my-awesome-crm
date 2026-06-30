import src.integrations.pipedrive as pipedrive

def test_public_api_exposure():
    """
    Verify that the integration module exposes exactly the interface 
    required by the host discovery and the AdditionalFunctionality specification.
    """
    # Check required attributes
    assert hasattr(pipedrive, "DATA_TYPE")
    assert hasattr(pipedrive, "fetch")
    assert pipedrive.DATA_TYPE == "contact"
    assert callable(pipedrive.fetch)
    
    # Check __all__ declaration
    assert set(pipedrive.__all__) == {"DATA_TYPE", "fetch"}

def test_module_namespace_protection():
    """
    Verify that internal implementation details like 'os' or 'httpx' 
    are not part of the intended public API via __all__.
    """
    assert "os" not in pipedrive.__all__
    assert "httpx" not in pipedrive.__all__
    assert "map_pipedrive_person_to_contact" not in pipedrive.__all__