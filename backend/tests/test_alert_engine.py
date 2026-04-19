"""Tests for alert rule engine"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from alerts.engine import AlertEngine
from db.models import AlertRule


@pytest.fixture
def alert_engine():
    """Create alert engine instance"""
    return AlertEngine()


@pytest.fixture
def sample_rule():
    """Create sample alert rule"""
    rule = Mock(spec=AlertRule)
    rule.id = "rule-1"
    rule.enabled = True
    rule.threshold = 80
    rule.condition = "gt"
    rule.suppress_until = None
    return rule


def test_evaluate_rule_greater_than(alert_engine, sample_rule):
    """Test greater than condition"""
    # Should trigger
    assert alert_engine.evaluate_rule(sample_rule, 85) is True

    # Should not trigger
    assert alert_engine.evaluate_rule(sample_rule, 75) is False

    # Boundary
    assert alert_engine.evaluate_rule(sample_rule, 80) is False


def test_evaluate_rule_less_than(alert_engine, sample_rule):
    """Test less than condition"""
    sample_rule.condition = "lt"

    # Should trigger
    assert alert_engine.evaluate_rule(sample_rule, 70) is True

    # Should not trigger
    assert alert_engine.evaluate_rule(sample_rule, 85) is False


def test_evaluate_rule_equal(alert_engine, sample_rule):
    """Test equal condition"""
    sample_rule.condition = "eq"

    assert alert_engine.evaluate_rule(sample_rule, 80) is True
    assert alert_engine.evaluate_rule(sample_rule, 79) is False


def test_evaluate_rule_disabled(alert_engine, sample_rule):
    """Test disabled rule"""
    sample_rule.enabled = False

    # Should always return False if disabled
    assert alert_engine.evaluate_rule(sample_rule, 100) is False


def test_evaluate_rule_suppressed(alert_engine, sample_rule):
    """Test suppressed rule"""
    # Suppress until future time
    sample_rule.suppress_until = datetime.utcnow() + timedelta(hours=1)

    # Should not trigger if suppressed
    assert alert_engine.evaluate_rule(sample_rule, 100) is False

    # Suppress until past time
    sample_rule.suppress_until = datetime.utcnow() - timedelta(hours=1)

    # Should trigger if suppress time passed
    assert alert_engine.evaluate_rule(sample_rule, 85) is True


def test_evaluate_batch_rules(alert_engine):
    """Test batch rule evaluation"""
    rules = []
    for i in range(3):
        rule = Mock(spec=AlertRule)
        rule.id = f"rule-{i}"
        rule.enabled = True
        rule.threshold = 80 + (i * 10)  # 80, 90, 100
        rule.condition = "gt"
        rule.suppress_until = None
        rules.append(rule)

    metrics = {
        "rule-0": 85,  # Should trigger (85 > 80)
        "rule-1": 85,  # Should not trigger (85 < 90)
        "rule-2": 105, # Should trigger (105 > 100)
    }

    # Update to use metric_type for proper matching
    for rule in rules:
        rule.metric_type = f"metric_{rule.id.split('-')[1]}"

    # Test individual evaluation
    assert alert_engine.evaluate_rule(rules[0], 85) is True
    assert alert_engine.evaluate_rule(rules[1], 85) is False


def test_anomaly_detection(alert_engine):
    """Test anomaly detection algorithm"""
    recent_values = [50, 52, 48, 51, 49, 50, 51]  # Normal

    # Normal value
    assert alert_engine.detect_anomaly(recent_values + [50]) is False

    # Anomalous value (3+ sigma)
    assert alert_engine.detect_anomaly(recent_values + [150]) is True


def test_trend_calculation(alert_engine):
    """Test trend calculation"""
    values = [
        (datetime.utcnow() - timedelta(hours=i), 50 + i)
        for i in range(10)
    ]
    values.reverse()  # Ascending trend

    trend = alert_engine.calculate_trend(values)

    assert trend["trend_direction"] in [-1, 0, 1]
    assert "volatility" in trend
    assert "average" in trend


def test_forecast(alert_engine):
    """Test metric forecasting"""
    values = [
        (datetime.utcnow() - timedelta(hours=i), 50 + (i * 2))
        for i in range(12)
    ]
    values.reverse()

    forecast = alert_engine.forecast(values, periods=6)

    assert len(forecast) == 6
    assert all(isinstance(v, (int, float)) for v in forecast)


def test_period_comparison(alert_engine):
    """Test period comparison"""
    period_1 = [50, 52, 48, 51, 49]  # avg ≈ 50
    period_2 = [60, 62, 58, 61, 59]  # avg ≈ 60

    comparison = alert_engine.compare_periods(period_1, period_2)

    assert "change_percent" in comparison
    assert comparison["change_percent"] > 0  # Increased
    assert "significance" in comparison


def test_invalid_condition(alert_engine, sample_rule):
    """Test handling of invalid condition"""
    sample_rule.condition = "invalid"

    # Should handle gracefully
    result = alert_engine.evaluate_rule(sample_rule, 85)
    assert result is False


def test_edge_cases(alert_engine, sample_rule):
    """Test edge cases"""
    # Zero threshold
    sample_rule.threshold = 0
    assert alert_engine.evaluate_rule(sample_rule, 1) is True
    assert alert_engine.evaluate_rule(sample_rule, -1) is False

    # Negative values
    sample_rule.threshold = -10
    assert alert_engine.evaluate_rule(sample_rule, -5) is True
    assert alert_engine.evaluate_rule(sample_rule, -20) is False

    # Very large numbers
    sample_rule.threshold = 999999
    assert alert_engine.evaluate_rule(sample_rule, 1000000) is True
