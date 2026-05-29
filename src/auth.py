import os
from fastapi import Header, HTTPException, status

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected_key = os.environ.get("CRM_API_KEY")
    
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    return x_api_key