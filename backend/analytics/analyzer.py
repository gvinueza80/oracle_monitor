"""Analytics and trend analysis"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from statistics import mean, stdev

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Metric, AlertHistory
from uuid import UUID

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes metrics trends and patterns"""

    @staticmethod
    def calculate_trend(
        values: List[Tuple[datetime, float]]
    ) -> Dict[str, float]:
        """
        Calculate trend statistics

        Returns:
            - trend_direction: -1 (decreasing), 0 (stable), 1 (increasing)
            - rate_of_change: % change per period
            - volatility: standard deviation
            - average: mean value
        """
        if len(values) < 2:
            return {
                "trend_direction": 0,
                "rate_of_change": 0,
                "volatility": 0,
                "average": values[0][1] if values else 0
            }

        metric_values = [v[1] for v in values]

        # Calculate statistics
        average = mean(metric_values)
        volatility = stdev(metric_values) if len(metric_values) > 1 else 0

        # Calculate trend using linear regression
        x_values = list(range(len(metric_values)))
        x_mean = mean(x_values)
        y_mean = average

        # Slope calculation
        numerator = sum(
            (x_values[i] - x_mean) * (metric_values[i] - y_mean)
            for i in range(len(metric_values))
        )
        denominator = sum(
            (x_values[i] - x_mean) ** 2
            for i in range(len(metric_values))
        )

        slope = numerator / denominator if denominator != 0 else 0

        # Determine trend direction
        trend_direction = 0
        if slope > volatility * 0.1:  # Increasing
            trend_direction = 1
        elif slope < -volatility * 0.1:  # Decreasing
            trend_direction = -1

        # Rate of change (%)
        if metric_values[0] != 0:
            rate_of_change = ((metric_values[-1] - metric_values[0]) / metric_values[0]) * 100
        else:
            rate_of_change = 0

        return {
            "trend_direction": trend_direction,
            "rate_of_change": round(rate_of_change, 2),
            "volatility": round(volatility, 2),
            "average": round(average, 2),
            "min": min(metric_values),
            "max": max(metric_values),
        }

    @staticmethod
    def forecast(
        values: List[Tuple[datetime, float]],
        periods: int = 24
    ) -> List[float]:
        """
        Simple exponential smoothing forecast

        Args:
            values: List of (timestamp, value) tuples
            periods: Number of periods to forecast

        Returns:
            List of forecasted values
        """
        if len(values) < 2:
            return [values[0][1]] * periods if values else []

        metric_values = [v[1] for v in values]

        # Exponential smoothing (alpha = 0.3)
        alpha = 0.3
        forecast = [metric_values[0]]

        for value in metric_values[1:]:
            next_forecast = alpha * value + (1 - alpha) * forecast[-1]
            forecast.append(next_forecast)

        # Project forward
        last_forecast = forecast[-1]
        for _ in range(periods):
            last_forecast = alpha * metric_values[-1] + (1 - alpha) * last_forecast
            forecast.append(last_forecast)

        return forecast[len(metric_values):]

    @staticmethod
    def detect_anomaly(
        recent_values: List[float],
        threshold_sigma: float = 3.0
    ) -> bool:
        """
        Detect anomalies using statistical method (3-sigma rule)

        Args:
            recent_values: List of recent metric values
            threshold_sigma: Standard deviation multiplier

        Returns:
            True if latest value is anomalous
        """
        if len(recent_values) < 3:
            return False

        values = recent_values[:-1]
        latest = recent_values[-1]

        avg = mean(values)
        std = stdev(values)

        # Check if latest value is outside threshold_sigma standard deviations
        return abs(latest - avg) > threshold_sigma * std

    @staticmethod
    def compare_periods(
        before: List[float],
        after: List[float]
    ) -> Dict[str, float]:
        """
        Compare metrics between two time periods

        Returns:
            - change_percent: % change from before to after
            - improvement: boolean indicating if better or worse
            - significance: how significant the change is (z-score)
        """
        if not before or not after:
            return {"change_percent": 0, "improvement": False, "significance": 0}

        avg_before = mean(before)
        avg_after = mean(after)

        if avg_before == 0:
            change_percent = 0
        else:
            change_percent = ((avg_after - avg_before) / avg_before) * 100

        # Simple significance test
        std_before = stdev(before) if len(before) > 1 else 0
        if std_before != 0:
            z_score = (avg_after - avg_before) / std_before
        else:
            z_score = 0

        return {
            "change_percent": round(change_percent, 2),
            "improvement": change_percent < 0,  # For metrics like response time
            "significance": round(z_score, 2),
            "avg_before": round(avg_before, 2),
            "avg_after": round(avg_after, 2),
        }


class MetricsAnalytics:
    """Provides analytics queries and reports"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analyzer = TrendAnalyzer()

    async def get_metric_trend(
        self,
        instance_id: UUID,
        metric_type: str,
        hours: int = 24
    ) -> Dict:
        """Get trend analysis for a metric"""
        period_start = datetime.utcnow() - timedelta(hours=hours)

        stmt = select(Metric).where(
            (Metric.instance_id == instance_id) &
            (Metric.metric_type == metric_type) &
            (Metric.collected_at >= period_start)
        ).order_by(Metric.collected_at)

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        if not metrics:
            return {"error": "No data available"}

        values = [(m.collected_at, m.metric_value) for m in metrics]
        trend = self.analyzer.calculate_trend(values)

        return {
            "metric_type": metric_type,
            "period_hours": hours,
            "data_points": len(metrics),
            **trend
        }

    async def get_metric_forecast(
        self,
        instance_id: UUID,
        metric_type: str,
        forecast_hours: int = 24
    ) -> Dict:
        """Get metric forecast"""
        period_start = datetime.utcnow() - timedelta(hours=72)

        stmt = select(Metric).where(
            (Metric.instance_id == instance_id) &
            (Metric.metric_type == metric_type) &
            (Metric.collected_at >= period_start)
        ).order_by(Metric.collected_at)

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        if not metrics:
            return {"error": "No data available"}

        values = [(m.collected_at, m.metric_value) for m in metrics]
        forecasted = self.analyzer.forecast(values, periods=forecast_hours)

        return {
            "metric_type": metric_type,
            "forecast_periods": forecast_hours,
            "forecasted_values": [round(v, 2) for v in forecasted],
            "latest_value": values[-1][1],
            "forecast_start": datetime.utcnow().isoformat()
        }

    async def detect_metric_anomalies(
        self,
        instance_id: UUID,
        metric_type: str,
        lookback_hours: int = 24
    ) -> Dict:
        """Detect anomalies in metrics"""
        period_start = datetime.utcnow() - timedelta(hours=lookback_hours)

        stmt = select(Metric).where(
            (Metric.instance_id == instance_id) &
            (Metric.metric_type == metric_type) &
            (Metric.collected_at >= period_start)
        ).order_by(Metric.collected_at)

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        if len(metrics) < 3:
            return {"error": "Insufficient data", "data_points": len(metrics)}

        metric_values = [m.metric_value for m in metrics]
        is_anomaly = self.analyzer.detect_anomaly(metric_values)

        anomalous_points = []
        if len(metric_values) >= 3:
            for i in range(2, len(metric_values)):
                if self.analyzer.detect_anomaly(metric_values[max(0, i-10):i+1]):
                    anomalous_points.append({
                        "index": i,
                        "value": metric_values[i],
                        "timestamp": metrics[i].collected_at.isoformat()
                    })

        return {
            "metric_type": metric_type,
            "is_anomaly": is_anomaly,
            "anomalous_points": anomalous_points,
            "data_points_analyzed": len(metrics),
            "detection_method": "3-sigma statistical"
        }

    async def compare_time_periods(
        self,
        instance_id: UUID,
        metric_type: str,
        period_1_hours: int = 24,
        period_2_hours: int = 24
    ) -> Dict:
        """Compare metrics between two time periods"""
        now = datetime.utcnow()
        period_2_start = now - timedelta(hours=period_2_hours)
        period_1_start = period_2_start - timedelta(hours=period_1_hours)

        # Get period 1 data
        stmt1 = select(Metric).where(
            (Metric.instance_id == instance_id) &
            (Metric.metric_type == metric_type) &
            (Metric.collected_at >= period_1_start) &
            (Metric.collected_at < period_2_start)
        )
        result1 = await self.db.execute(stmt1)
        metrics1 = result1.scalars().all()

        # Get period 2 data
        stmt2 = select(Metric).where(
            (Metric.instance_id == instance_id) &
            (Metric.metric_type == metric_type) &
            (Metric.collected_at >= period_2_start)
        )
        result2 = await self.db.execute(stmt2)
        metrics2 = result2.scalars().all()

        if not metrics1 or not metrics2:
            return {"error": "Insufficient data for comparison"}

        values1 = [m.metric_value for m in metrics1]
        values2 = [m.metric_value for m in metrics2]

        comparison = self.analyzer.compare_periods(values1, values2)

        return {
            "metric_type": metric_type,
            "period_1": {
                "hours": period_1_hours,
                "data_points": len(metrics1),
                "avg": round(mean(values1), 2)
            },
            "period_2": {
                "hours": period_2_hours,
                "data_points": len(metrics2),
                "avg": round(mean(values2), 2)
            },
            **comparison
        }

    async def get_alert_patterns(
        self,
        instance_id: UUID,
        days: int = 7
    ) -> Dict:
        """Analyze alert patterns"""
        period_start = datetime.utcnow() - timedelta(days=days)

        stmt = select(AlertHistory).where(
            (AlertHistory.triggered_at >= period_start) &
            (AlertHistory.rule_id.in_(
                select(AlertHistory.rule_id).where(
                    AlertHistory.triggered_at >= period_start
                )
            ))
        )

        result = await self.db.execute(stmt)
        alerts = result.scalars().all()

        if not alerts:
            return {"error": "No alerts in period", "days": days}

        # Count by severity
        severity_counts = {}
        for alert in alerts:
            # Would need to join with AlertRule to get severity
            pass

        # Count by status
        status_counts = {}
        for alert in alerts:
            status = alert.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Time to resolution
        resolved_alerts = [a for a in alerts if a.resolved_at]
        if resolved_alerts:
            resolutions_times = [
                (a.resolved_at - a.triggered_at).total_seconds() / 3600
                for a in resolved_alerts
            ]
            avg_resolution_time = mean(resolutions_times)
        else:
            avg_resolution_time = None

        return {
            "period_days": days,
            "total_alerts": len(alerts),
            "status_breakdown": status_counts,
            "avg_resolution_hours": round(avg_resolution_time, 2) if avg_resolution_time else None,
            "resolved_count": len(resolved_alerts)
        }
