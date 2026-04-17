"""Authentication endpoints (login, token refresh)"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password
)
from db import get_db
from db.models import User, Role

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    """
    try:
        # Query user by username
        stmt = select(User).where(User.username == request.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Get user permissions from roles
        stmt = select(Role).where(Role.id.in_(
            select(Role.id).select_from(User.__table__.join(
                Role.__table__, User.__table__.c.id
            )).where(User.id == user.id)
        ))
        result = await db.execute(stmt)
        roles = result.scalars().all()

        permissions = []
        for role in roles:
            permissions.extend(role.permissions)

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
            "permissions": list(set(permissions))
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        logger.info(f"User {request.username} logged in")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh an access token using a refresh token
    """
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Create new access token
    token_data = {
        "sub": payload.get("sub"),
        "username": payload.get("username"),
        "is_admin": payload.get("is_admin", False),
        "permissions": payload.get("permissions", [])
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint (token revocation in production)
    """
    # In production: revoke the token in Redis
    return {"message": "Logged out successfully"}
