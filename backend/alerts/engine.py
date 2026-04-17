"""Alert rule evaluation engine"""

import logging
from datetime import datetime, timedelta

from db.models import AlertRule

logger = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates alert rules against metrics"""

    OPERATORS = {
        'gt': lambda metric, threshold: metric > threshold,
        'lt': lambda metric, threshold: metric < threshold,
        'eq': lambda metric, threshold: metric == threshold,
        'gte': lambda metric, threshold: metric >= threshold,
        'lte': lambda metric, threshold: metric <= threshold,
    }

    def evaluate_rule(self, rule: AlertRule, metric_value: float) -> bool:
        """
        Evaluate if an alert rule is triggered

        Args:
            rule: AlertRule model instance
            metric_value: Current metric value

        Returns:
            True if alert should be triggered, False otherwise
        """
        if not rule.enabled:
            return False

        # Check suppression
        if rule.suppress_until and rule.suppress_until > datetime.utcnow():
            logger.debug(f"Alert {rule.id} is suppressed until {rule.suppress_until}")
            return False

        # Get the operator function
        operator = self.OPERATORS.get(rule.condition)
        if not operator:
            logger.error(f"Unknown condition: {rule.condition}")
            return False

        # Evaluate the condition
        try:
            triggered = operator(metric_value, float(rule.threshold))
            return triggered
        except (ValueError, TypeError) as e:
            logger.error(f"Error evaluating rule {rule.id}: {e}")
            return False

    def evaluate_rules_batch(self, rules: list, metrics: dict) -> list:
        """
        Evaluate multiple rules against metrics

        Args:
            rules: List of AlertRule instances
            metrics: Dict of {metric_type: metric_value}

        Returns:
            List of triggered rule IDs
        """
        triggered = []

        for rule in rules:
            metric_value = metrics.get(rule.metric_type)
            if metric_value is not None:
                if self.evaluate_rule(rule, metric_value):
                    triggered.append(rule.id)

        return triggered

    def check_sustained_condition(
        self,
        rule: AlertRule,
        metric_values: list,
        check_duration: int
    ) -> bool:
        """
        Check if a condition is sustained over a time period

        Args:
            rule: AlertRule instance
            metric_values: List of (timestamp, value) tuples
            check_duration: Duration in seconds to check

        Returns:
            True if condition is sustained throughout the period
        """
        if not metric_values:
            return False

        operator = self.OPERATORS.get(rule.condition)
        if not operator:
            return False

        threshold = float(rule.threshold)

        # Filter values within the check duration
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=check_duration)

        relevant_values = [
            value for timestamp, value in metric_values
            if timestamp >= cutoff_time
        ]

        if not relevant_values:
            return False

        # Check if all values trigger the condition
        return all(
            operator(value, threshold)
            for value in relevant_values
        )
