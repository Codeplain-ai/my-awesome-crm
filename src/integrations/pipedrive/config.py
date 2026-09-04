import os

def get_api_token() -> str:
    """Read Pipedrive API token from environment."""
    token = os.environ.get("PIPEDRIVE_API_TOKEN")
    if not token:
        raise RuntimeError("Environment variable 'PIPEDRIVE_API_TOKEN' is missing or empty")
    return token


def get_company_domain() -> str:
    """Read Pipedrive company subdomain from environment."""
    domain = os.environ.get("PIPEDRIVE_COMPANY_DOMAIN")
    if not domain:
        raise RuntimeError("Environment variable 'PIPEDRIVE_COMPANY_DOMAIN' is missing or empty")
    return domain