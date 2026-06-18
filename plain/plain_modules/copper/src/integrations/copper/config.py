import os

def get_credentials() -> dict[str, str]:
    """
    Retrieves Copper credentials from environment variables.
    Raises RuntimeError if required variables are missing.
    """
    api_key = os.environ.get("COPPER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: COPPER_API_KEY")
        
    user_email = os.environ.get("COPPER_USER_EMAIL")
    if not user_email:
        raise RuntimeError("Missing environment variable: COPPER_USER_EMAIL")
        
    return {
        "X-PW-AccessToken": api_key,
        "X-PW-UserEmail": user_email,
        "X-PW-Application": "developer_api",
        "Content-Type": "application/json"
    }