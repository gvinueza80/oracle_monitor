"""Metrics API endpoints"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

router = APIRouter()


@router.get("/overview")
async def get_overview():
    """Get overview metrics (sessions, locks, tablespace, slow queries)"""
    return {
        "active_sessions": 0,
        "locked_sessions": 0,
        "tablespace_used_percent": 0,
        "slow_queries_count": 0,
        "last_update": datetime.utcnow().isoformat()
    }


@router.get("/sessions")
async def get_sessions(
    instance_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get active sessions for an instance"""
    return {
        "sessions": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/locks")
async def get_locks(instance_id: str = Query(...)):
    """Get lock information"""
    return {
        "locks": [],
        "blockers": [],
        "last_update": datetime.utcnow().isoformat()
    }


@router.get("/slow-queries")
async def get_slow_queries(
    instance_id: str = Query(...),
    limit: int = Query(10, ge=1, le=100)
):
    """Get slow queries"""
    return {
        "queries": [],
        "count": 0
    }


@router.get("/tablespace")
async def get_tablespace(instance_id: str = Query(...)):
    """Get tablespace usage"""
    return {
        "tablespaces": [],
        "total_size_gb": 0,
        "used_size_gb": 0
    }


@router.get("/{metric_type}/history")
async def get_metric_history(
    metric_type: str,
    instance_id: str = Query(...),
    hours: int = Query(24, ge=1, le=730)
):
    """Get historical metric data"""
    return {
        "metric_type": metric_type,
        "data_points": [],
        "period_start": datetime.utcnow().isoformat(),
        "period_hours": hours
    }
