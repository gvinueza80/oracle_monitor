"""FastAPI dependencies for authentication and authorization"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from security.jwt import decode_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    """
    Dependency to extract and validate JWT from request
    Returns the decoded token payload
    """
    token = credentials.credentials

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user is an admin
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def require_permission(permission: str):
    """
    Factory to create a dependency that requires a specific permission
    """
    async def check_permission(current_user: dict = Depends(get_current_user)) -> dict:
        user_permissions = current_user.get("permissions", [])

        if permission not in user_permissions and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

        return current_user

    return check_permission
