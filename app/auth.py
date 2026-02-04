"""Authentication module for CourseAlign API."""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import config

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify Bearer token authentication.
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Token string if valid
        
    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    if not config.api_secret:
        raise HTTPException(
            status_code=500,
            detail="API secret not configured on server"
        )
    
    if credentials.credentials != config.api_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    
    return credentials.credentials
