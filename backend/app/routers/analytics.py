"""Analytics and reporting endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import Instance
from analytics.analyzer import MetricsAnalytics
from security.dependencies import get_current_user
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics/{metric_type}/trend")
async def get_metric_trend(
    metric_type: str,
    instance_id: UUID = Query(...),
    hours: int = Query(24, ge=1, le=730),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trend analysis for a metric

    Returns trend direction, volatility, rate of change
    """
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        analytics = MetricsAnalytics(db)
        trend = await analytics.get_metric_trend(instance_id, metric_type, hours)

        return trend

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metric trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze trend"
        )


@router.get("/metrics/{metric_type}/forecast")
async def forecast_metric(
    metric_type: str,
    instance_id: UUID = Query(...),
    forecast_hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Forecast metric values using exponential smoothing

    Returns forecasted values for next N hours
    """
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        analytics = MetricsAnalytics(db)
        forecast = await analytics.get_metric_forecast(
            instance_id,
            metric_type,
            forecast_hours
        )

        return forecast

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forecasting metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to forecast metric"
        )


@router.get("/metrics/{metric_type}/anomalies")
async def detect_anomalies(
    metric_type: str,
    instance_id: UUID = Query(...),
    lookback_hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect anomalies in metric data using statistical analysis

    Uses 3-sigma rule to identify outliers
    """
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        analytics = MetricsAnalytics(db)
        anomalies = await analytics.detect_metric_anomalies(
            instance_id,
            metric_type,
            lookback_hours
        )

        return anomalies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect anomalies"
        )


@router.get("/metrics/{metric_type}/compare")
async def compare_periods(
    metric_type: str,
    instance_id: UUID = Query(...),
    period_1_hours: int = Query(24, ge=1, le=730),
    period_2_hours: int = Query(24, ge=1, le=730),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare metric values between two time periods

    Shows change percentage, statistical significance
    """
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        analytics = MetricsAnalytics(db)
        comparison = await analytics.compare_time_periods(
            instance_id,
            metric_type,
            period_1_hours,
            period_2_hours
        )

        return comparison

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing periods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare periods"
        )


@router.get("/alerts/patterns")
async def get_alert_patterns(
    instance_id: UUID = Query(...),
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze alert patterns over time

    Returns alert frequency, resolution time, status breakdown
    """
    try:
        # Verify instance exists
        stmt = select(Instance).where(Instance.id == instance_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )

        analytics = MetricsAnalytics(db)
        patterns = await analytics.get_alert_patterns(instance_id, days)

        return patterns

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get alert patterns"
        )


@router.get("/report/daily")
async def generate_daily_report(
    instance_id: UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate daily report for an instance

    Includes summary of metrics, alerts, and key events
    """
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

        analytics = MetricsAnalytics(db)

        # Collect report data
        cpu_trend = await analytics.get_metric_trend(instance_id, "cpu_usage", hours=24)
        memory_trend = await analytics.get_metric_trend(instance_id, "memory_shared_pool_mb", hours=24)
        alert_patterns = await analytics.get_alert_patterns(instance_id, days=1)

        report = {
            "instance_id": str(instance_id),
            "instance_name": instance.name,
            "report_date": __import__('datetime').datetime.utcnow().isoformat(),
            "metrics": {
                "cpu": cpu_trend,
                "memory": memory_trend,
            },
            "alerts": alert_patterns,
            "summary": {
                "period": "24 hours",
                "status": "generated"
            }
        }

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )
