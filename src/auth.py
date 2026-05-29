import os
from fastapi import Header, HTTPException, status

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected_key = os.environ.get("CRM_API_KEY")
    
    if not expected_key:
        # This case is caught by the startup lifecycle, but we protect the route
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key not configured on server"
        )
        
    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    return x_api_key