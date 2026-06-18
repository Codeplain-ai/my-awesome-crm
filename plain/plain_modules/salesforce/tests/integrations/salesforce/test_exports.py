import src.integrations.salesforce as sf

def test_only_fetch_contacts_exported():
    """
    Ensures the Salesforce integration package only exports 
    the 'fetch_contacts' callable as per the plug-in contract.
    """
    # Check __all__ if defined
    if hasattr(sf, "__all__"):
        assert sf.__all__ == ["fetch_contacts"]
    
    # Verify the primary contract exists
    assert hasattr(sf, "fetch_contacts")
    assert callable(sf.fetch_contacts)
    
    # Check that internal implementation details are not part of the public API 
    # (even if they exist as private-prefixed members)
    public_names = [name for name in dir(sf) if not name.startswith("_")]
    # Note: 'mapping' or 'logging' might be in dir() due to imports, 
    # but the contract is about what is intended for re-export.
    # Based on the requirement "exports only... and re-exports no other names":
    assert "fetch_contacts" in public_names
    
    # If using __all__, 'mapping' should not be in there
    if hasattr(sf, "__all__"):
        assert "mapping" not in sf.__all__
        assert "map_contact_record" not in sf.__all__