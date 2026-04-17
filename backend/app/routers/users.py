"""User management endpoints (admin only)"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, UsersResponse
from security.jwt import hash_password
from security.dependencies import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=UsersResponse)
async def list_users(
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    try:
        stmt = select(User).order_by(User.username)
        result = await db.execute(stmt)
        users = result.scalars().all()

        return UsersResponse(
            users=users,
            total=len(users)
        )

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user"""
    try:
        # Check if user already exists
        stmt = select(User).where(User.username == user_data.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{user_data.username}' already exists"
            )

        # Check if email already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{user_data.email}' already registered"
            )

        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            is_admin=user_data.is_admin,
            is_active=True
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"User created: {user.id}")

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user details"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        logger.info(f"User updated: {user_id}")

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent deleting current user
        if str(user.id) == current_user.get('sub'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own user account"
            )

        await db.delete(user)
        await db.commit()

        logger.info(f"User deleted: {user_id}")

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
