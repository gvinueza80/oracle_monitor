"""User management endpoints (admin only)"""

from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter()


@router.get("/")
async def list_users():
    """List all users (admin only)"""
    return {
        "users": [],
        "count": 0
    }


@router.post("/")
async def create_user(user_data: dict):
    """Create a new user"""
    return {
        "user_id": "new-user-id",
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    return {
        "user_id": user_id,
        "username": "username",
        "roles": []
    }


@router.put("/{user_id}")
async def update_user(user_id: str, user_data: dict):
    """Update user"""
    return {
        "user_id": user_id,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user"""
    return {
        "user_id": user_id,
        "deleted_at": datetime.utcnow().isoformat()
    }
