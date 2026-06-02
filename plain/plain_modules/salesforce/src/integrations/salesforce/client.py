import os
from typing import Any
from simple_salesforce import Salesforce
from src.integrations.salesforce.mapping import salesforce_contact_to_incoming

def _get_credentials() -> dict[str, str]:
    """Reads Salesforce credentials from environment variables."""
    creds = {
        "username": os.environ.get("SF_USERNAME", ""),
        "password": os.environ.get("SF_PASSWORD", ""),
        "security_token": os.environ.get("SF_SECURITY_TOKEN", ""),
        "domain": os.environ.get("SF_DOMAIN") or "login",
    }
    
    for key in ["username", "password", "security_token"]:
        if not creds[key]:
            raise RuntimeError(f"Missing required Salesforce credential: SF_{key.upper()}")
            
    return creds

def _build_client(creds: dict[str, str]) -> Salesforce:
    """Indirection point for creating the Salesforce client for testing."""
    return Salesforce(
        username=creds["username"],
        password=creds["password"],
        security_token=creds["security_token"],
        domain=creds["domain"]
    )

def _run_query(sf: Salesforce, soql: str) -> dict[str, Any]:
    """Indirection point for running the SOQL query for testing."""
    # query_all handles Salesforce pagination (query_more) automatically
    return sf.query_all(soql)

def fetch_contacts() -> list[dict[str, Any]]:
    """
    Main entry point for the Salesforce integration discovered by the host.
    """
    creds = _get_credentials()
    sf = _build_client(creds)
    
    soql = "SELECT Id, Name, FirstName, LastName, Email, Phone, Title, Account.Name FROM Contact"
    query_result = _run_query(sf, soql)
    
    records = query_result.get("records", [])
    
    return [salesforce_contact_to_incoming(record) for record in records]