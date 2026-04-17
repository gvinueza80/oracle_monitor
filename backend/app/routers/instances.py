"""Database instance management endpoints"""

from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter()


@router.get("/")
async def list_instances():
    """List all configured Oracle instances"""
    return {
        "instances": [],
        "count": 0
    }


@router.post("/")
async def create_instance(instance_data: dict):
    """Register a new Oracle instance"""
    return {
        "instance_id": "new-instance-id",
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/{instance_id}")
async def get_instance(instance_id: str):
    """Get instance details"""
    return {
        "instance_id": instance_id,
        "name": "Instance Name",
        "status": "connected"
    }


@router.put("/{instance_id}")
async def update_instance(instance_id: str, instance_data: dict):
    """Update instance configuration"""
    return {
        "instance_id": instance_id,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.delete("/{instance_id}")
async def delete_instance(instance_id: str):
    """Remove an instance"""
    return {
        "instance_id": instance_id,
        "deleted_at": datetime.utcnow().isoformat()
    }


@router.post("/{instance_id}/test-connection")
async def test_connection(instance_id: str):
    """Test connection to an instance"""
    return {
        "instance_id": instance_id,
        "connected": True,
        "message": "Connection successful"
    }
