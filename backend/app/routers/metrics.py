"""Metrics API endpoints"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends, HTTPException, status

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import (
    Instance, Metric, ActiveSession, Lock, SlowQuery, AlertHistory
)
from app.schemas import (
    MetricsHistoryResponse, OverviewMetricsResponse, SessionsResponse,
    LocksResponse, SlowQueriesResponse, TablespacesResponse, MetricResponse
)
from security.dependencies import get_current_user
from cache.redis_cache import redis_cache, instance_metrics_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=OverviewMetricsResponse)
async def get_overview(
    instance_id: UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overview metrics (sessions, locks, tablespace, slow queries)"""
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        # Get active sessions count
        stmt = select(func.count(ActiveSession.id)).where(
            ActiveSession.instance_id == instance_id
        )
        result = await db.execute(stmt)
        active_sessions = result.scalar() or 0

        # Get locked sessions count
        stmt = select(func.count(Lock.id)).where(
            and_(
                Lock.instance_id == instance_id,
                Lock.resolved_at.is_(None)
            )
        )
        result = await db.execute(stmt)
        locked_sessions = result.scalar() or 0

        # Get latest tablespace usage
        stmt = select(func.avg(Metric.metric_value)).where(
            and_(
                Metric.instance_id == instance_id,
                Metric.metric_type == 'tablespace_usage'
            )
        ).order_by(desc(Metric.collected_at)).limit(1)
        result = await db.execute(stmt)
        tablespace_percent = result.scalar() or 0.0

        # Get slow queries count
        stmt = select(func.count(SlowQuery.id)).where(
            SlowQuery.instance_id == instance_id
        )
        result = await db.execute(stmt)
        slow_queries = result.scalar() or 0

        # Get critical and warning alerts
        stmt = select(func.count(AlertHistory.id)).where(
            and_(
                AlertHistory.status == 'triggered',
                AlertHistory.rule_id.in_(
                    select(AlertHistory.rule_id).where(
                        AlertHistory.status == 'triggered'
                    )
                )
            )
        )
        result = await db.execute(stmt)
        total_alerts = result.scalar() or 0

        # Determine health status
        if locked_sessions > 0 or tablespace_percent > 95:
            health = "critical"
        elif active_sessions > 200 or tablespace_percent > 80:
            health = "degraded"
        else:
            health = "healthy"

        return OverviewMetricsResponse(
            active_sessions=active_sessions,
            locked_sessions=locked_sessions,
            tablespace_used_percent=float(tablespace_percent),
            slow_queries_count=slow_queries,
            critical_alerts=min(total_alerts, 99),
            warning_alerts=max(0, total_alerts - 10),
            instance_health_status=health,
            last_update=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching overview metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch metrics"
        )


@router.get("/sessions", response_model=SessionsResponse)
async def get_sessions(
    instance_id: UUID = Query(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active sessions for an instance"""
    try:
        # Get total count
        stmt = select(func.count(ActiveSession.id)).where(
            ActiveSession.instance_id == instance_id
        )
        result = await db.execute(stmt)
        total = result.scalar() or 0

        # Get paginated sessions
        stmt = select(ActiveSession).where(
            ActiveSession.instance_id == instance_id
        ).order_by(desc(ActiveSession.logon_time)).limit(limit).offset(offset)

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        return SessionsResponse(
            sessions=sessions,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sessions"
        )


@router.get("/locks", response_model=LocksResponse)
async def get_locks(
    instance_id: UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get lock information"""
    try:
        # Get unresolved locks
        stmt = select(Lock).where(
            and_(
                Lock.instance_id == instance_id,
                Lock.resolved_at.is_(None)
            )
        ).order_by(desc(Lock.detected_at))

        result = await db.execute(stmt)
        locks = result.scalars().all()

        # Extract unique blockers
        blockers = list(set(lock.blocker_session_id for lock in locks))

        return LocksResponse(
            locks=locks,
            blockers=blockers,
            last_update=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error fetching locks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch locks"
        )


@router.get("/slow-queries", response_model=SlowQueriesResponse)
async def get_slow_queries(
    instance_id: UUID = Query(...),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get slow queries"""
    try:
        stmt = select(SlowQuery).where(
            SlowQuery.instance_id == instance_id
        ).order_by(desc(SlowQuery.avg_duration_ms)).limit(limit)

        result = await db.execute(stmt)
        queries = result.scalars().all()

        return SlowQueriesResponse(
            queries=queries,
            count=len(queries)
        )

    except Exception as e:
        logger.error(f"Error fetching slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch slow queries"
        )


@router.get("/tablespace", response_model=TablespacesResponse)
async def get_tablespace(
    instance_id: UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tablespace usage"""
    try:
        # Get latest tablespace metrics (grouped by tablespace name via tags)
        stmt = select(Metric).where(
            and_(
                Metric.instance_id == instance_id,
                Metric.metric_type == 'tablespace_usage'
            )
        ).order_by(desc(Metric.collected_at)).limit(100)

        result = await db.execute(stmt)
        metrics = result.scalars().all()

        # Group by tablespace name from tags
        tablespace_map = {}
        for metric in metrics:
            if metric.tags and 'tablespace_name' in metric.tags:
                ts_name = metric.tags['tablespace_name']
                if ts_name not in tablespace_map:
                    tablespace_map[ts_name] = metric

        # Build response
        tablespaces = [
            {
                "tablespace_name": ts_name,
                "total_size_mb": 1024,  # Would come from Oracle query
                "free_space_mb": (1024 * (100 - metric.metric_value)) / 100,
                "used_percent": metric.metric_value
            }
            for ts_name, metric in tablespace_map.items()
        ]

        total_used = sum(ts['used_percent'] for ts in tablespaces) / len(tablespaces) if tablespaces else 0

        return TablespacesResponse(
            tablespaces=tablespaces,
            total_size_gb=float(len(tablespaces)),
            used_size_gb=float(total_used),
            total_count=len(tablespaces)
        )

    except Exception as e:
        logger.error(f"Error fetching tablespace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tablespace"
        )


@router.get("/{metric_type}/history", response_model=MetricsHistoryResponse)
async def get_metric_history(
    metric_type: str,
    instance_id: UUID = Query(...),
    hours: int = Query(24, ge=1, le=730),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get historical metric data"""
    try:
        period_start = datetime.utcnow() - timedelta(hours=hours)

        stmt = select(Metric).where(
            and_(
                Metric.instance_id == instance_id,
                Metric.metric_type == metric_type,
                Metric.collected_at >= period_start
            )
        ).order_by(Metric.collected_at)

        result = await db.execute(stmt)
        metrics = result.scalars().all()

        data_points = [
            MetricResponse.model_validate(m)
            for m in metrics
        ]

        return MetricsHistoryResponse(
            metric_type=metric_type,
            data_points=data_points,
            period_start=period_start,
            period_end=datetime.utcnow(),
            period_hours=hours,
            total_points=len(data_points)
        )

    except Exception as e:
        logger.error(f"Error fetching metric history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch metric history"
        )
