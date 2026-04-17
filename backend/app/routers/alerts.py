"""Alerts API endpoints"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends, HTTPException, status

from sqlalchemy import select, func, desc, and_

from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import AlertRule, AlertHistory, Instance
from app.schemas import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse, AlertRulesResponse,
    AlertsResponse, AlertAcknowledgeRequest, AlertResolveRequest
)
from security.dependencies import get_current_user, require_permission
from cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AlertsResponse)
async def get_alerts(
    instance_id: UUID = Query(...),
    severity: Optional[str] = Query(None, regex="info|warning|critical"),
    status_filter: Optional[str] = Query(None, regex="triggered|acknowledged|resolved"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get alerts for an instance"""
    try:
        # Build query
        stmt = select(AlertHistory).where(
            AlertHistory.rule_id.in_(
                select(AlertRule.id).where(AlertRule.instance_id == instance_id)
            )
        )

        if severity:
            stmt = stmt.where(
                AlertHistory.rule_id.in_(
                    select(AlertRule.id).where(AlertRule.severity == severity)
                )
            )

        if status_filter:
            stmt = stmt.where(AlertHistory.status == status_filter)

        # Get total count
        count_stmt = select(func.count()).select_from(AlertHistory).where(
            AlertHistory.rule_id.in_(
                select(AlertRule.id).where(AlertRule.instance_id == instance_id)
            )
        )
        result = await db.execute(count_stmt)
        total = result.scalar() or 0

        # Get paginated results
        stmt = stmt.order_by(desc(AlertHistory.triggered_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return AlertsResponse(
            alerts=alerts,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alerts"
        )


@router.get("/rules", response_model=AlertRulesResponse)
async def get_alert_rules(
    instance_id: UUID = Query(...),
    enabled_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get alert rules for an instance"""
    try:
        stmt = select(AlertRule).where(AlertRule.instance_id == instance_id)

        if enabled_only:
            stmt = stmt.where(AlertRule.enabled == True)

        result = await db.execute(stmt.order_by(AlertRule.name))
        rules = result.scalars().all()

        return AlertRulesResponse(
            rules=rules,
            count=len(rules)
        )

    except Exception as e:
        logger.error(f"Error fetching alert rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alert rules"
        )


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    instance_id: UUID = Query(...),
    rule_data: AlertRuleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new alert rule"""
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        # Create rule
        alert_rule = AlertRule(
            instance_id=instance_id,
            name=rule_data.name,
            description=rule_data.description,
            metric_type=rule_data.metric_type,
            threshold=rule_data.threshold,
            condition=rule_data.condition,
            check_duration=rule_data.check_duration,
            severity=rule_data.severity,
            enabled=rule_data.enabled,
            notifications=rule_data.notifications,
            auto_remediation_enabled=rule_data.auto_remediation_enabled,
            auto_remediation_action=rule_data.auto_remediation_action,
            created_by=UUID(current_user.get('sub'))
        )

        db.add(alert_rule)
        await db.commit()
        await db.refresh(alert_rule)

        logger.info(f"Alert rule created: {alert_rule.id}")

        return AlertRuleResponse.model_validate(alert_rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert rule"
        )


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific alert rule"""
    try:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )

        return AlertRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alert rule"
        )


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    rule_data: AlertRuleUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an alert rule"""
    try:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )

        # Update fields
        update_data = rule_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        rule.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(rule)

        logger.info(f"Alert rule updated: {rule_id}")

        return AlertRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert rule: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alert rule"
        )


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an alert rule"""
    try:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )

        await db.delete(rule)
        await db.commit()

        logger.info(f"Alert rule deleted: {rule_id}")

        return {"message": "Alert rule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert rule: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert rule"
        )


@router.post("/{alert_id}/acknowledge", response_model=AlertsResponse)
async def acknowledge_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert"""
    try:
        stmt = select(AlertHistory).where(AlertHistory.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = UUID(current_user.get('sub'))
        alert.status = 'acknowledged'

        await db.commit()

        logger.info(f"Alert acknowledged: {alert_id}")

        return {"message": "Alert acknowledged successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert"
        )


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    request: AlertResolveRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert"""
    try:
        stmt = select(AlertHistory).where(AlertHistory.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        alert.resolved_at = datetime.utcnow()
        alert.status = 'resolved'

        await db.commit()

        logger.info(f"Alert resolved: {alert_id}")

        return {"message": "Alert resolved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert"
        )
