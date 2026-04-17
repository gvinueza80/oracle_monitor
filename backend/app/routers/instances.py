"""Database instance management endpoints"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import Instance, AuditLog
from db.oracle_client import OracleConnectionPool
from app.schemas import (
    InstanceCreate, InstanceUpdate, InstanceResponse, InstanceListResponse
)
from security.dependencies import get_current_user, require_permission
from cache.redis_cache import redis_cache, instance_health_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=InstanceListResponse)
async def list_instances(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all configured Oracle instances"""
    try:
        stmt = select(Instance).order_by(Instance.name)
        result = await db.execute(stmt)
        instances = result.scalars().all()

        return InstanceListResponse(
            instances=instances,
            total=len(instances),
            limit=len(instances),
            offset=0
        )

    except Exception as e:
        logger.error(f"Error fetching instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch instances"
        )


@router.post("/", response_model=InstanceResponse)
async def create_instance(
    instance_data: InstanceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new Oracle instance"""
    try:
        # Check if instance with same name already exists
        stmt = select(Instance).where(Instance.name == instance_data.name)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Instance '{instance_data.name}' already exists"
            )

        # Create instance
        instance = Instance(
            name=instance_data.name,
            description=instance_data.description,
            host=instance_data.host,
            port=instance_data.port,
            service_name=instance_data.service_name,
            username=instance_data.username,
            password_encrypted=instance_data.password.encode('utf-8'),
            ssl_enabled=instance_data.ssl_enabled,
            connection_timeout=instance_data.connection_timeout,
            pool_min=instance_data.pool_min,
            pool_max=instance_data.pool_max,
            created_by=UUID(current_user.get('sub'))
        )

        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        # Log audit event
        audit_log = AuditLog(
            user_id=UUID(current_user.get('sub')),
            action='create',
            resource_type='instance',
            resource_id=str(instance.id),
            details={'name': instance.name, 'host': instance.host}
        )
        db.add(audit_log)
        await db.commit()

        logger.info(f"Instance created: {instance.id}")

        return InstanceResponse.model_validate(instance)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating instance: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create instance"
        )


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get instance details"""
    try:
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        return InstanceResponse.model_validate(instance)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching instance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch instance"
        )


@router.put("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: UUID,
    instance_data: InstanceUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update instance configuration"""
    try:
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        # Update fields
        update_data = instance_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'password':
                setattr(instance, 'password_encrypted', value.encode('utf-8'))
            else:
                setattr(instance, field, value)

        instance.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(instance)

        # Log audit event
        audit_log = AuditLog(
            user_id=UUID(current_user.get('sub')),
            action='update',
            resource_type='instance',
            resource_id=str(instance.id),
            details=dict(update_data)
        )
        db.add(audit_log)
        await db.commit()

        logger.info(f"Instance updated: {instance_id}")

        return InstanceResponse.model_validate(instance)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating instance: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update instance"
        )


@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove an instance"""
    try:
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        await db.delete(instance)
        await db.commit()

        # Log audit event
        audit_log = AuditLog(
            user_id=UUID(current_user.get('sub')),
            action='delete',
            resource_type='instance',
            resource_id=str(instance.id),
            details={'name': instance.name}
        )
        db.add(audit_log)
        await db.commit()

        logger.info(f"Instance deleted: {instance_id}")

        return {"message": "Instance deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting instance: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete instance"
        )


@router.post("/{instance_id}/test-connection")
async def test_connection(
    instance_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test connection to an instance"""
    try:
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        # Decrypt password
        password = instance.password_encrypted.decode('utf-8')

        # Test connection
        pool = OracleConnectionPool(
            username=instance.username,
            password=password,
            host=instance.host,
            port=instance.port,
            service_name=instance.service_name,
            instance_name=instance.name
        )

        connected = pool.test_connection()
        pool.close()

        # Update instance status
        instance.last_connection_check = datetime.utcnow()
        instance.connection_status = "connected" if connected else "failed"
        await db.commit()

        # Cache health status
        await redis_cache.set_json(
            instance_health_key(str(instance.id)),
            {
                "connected": connected,
                "last_check": datetime.utcnow().isoformat()
            },
            ttl=300
        )

        logger.info(f"Connection test for {instance.name}: {'successful' if connected else 'failed'}")

        return {
            "instance_id": instance_id,
            "connected": connected,
            "message": "Connection successful" if connected else "Connection failed",
            "last_check": instance.last_connection_check
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test connection"
        )
