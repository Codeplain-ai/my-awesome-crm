from typing import Any, Callable, List

from .mapping import map_account, map_contact

__all__ = ["fetch"]


def fetch(get_stored: Callable[[str], List[dict[str, Any]]]) -> List[dict[str, Any]]:
    """
    Primary entry point for the Salesforce integration.
    Pulls Contacts and Accounts from Salesforce REST API.
    """
    from .client import SalesforceClient

    client = SalesforceClient()
    
    # 1. Fetch Contacts
    contact_soql = (
        "SELECT Id, Name, FirstName, LastName, Email, Phone, MobilePhone, "
        "Title, Account.Name FROM Contact"
    )
    raw_contacts = client.query_all(contact_soql)
    mapped_contacts = [
        {"data_type": "contact", "data": map_contact(r)}
        for r in raw_contacts
    ]

    # 2. Fetch Accounts
    account_soql = "SELECT Id, Name, Website, Phone, Industry FROM Account"
    raw_accounts = client.query_all(account_soql)
    mapped_accounts = [
        {"data_type": "account", "data": map_account(r)}
        for r in raw_accounts
    ]

    return mapped_contacts + mapped_accounts