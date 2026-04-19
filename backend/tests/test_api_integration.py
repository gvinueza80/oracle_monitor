"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.main import app
from db.models import User, Role, Instance, Metric, AlertRule, AlertHistory
from security.jwt import create_access_token


@pytest.fixture
def client(db_session):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def test_user(db_session):
    """Create test user with admin role"""
    from app.config import settings

    role = Role(name="admin", permissions=["metrics:read", "alerts:manage"])
    db_session.add(role)
    await db_session.flush()

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$test",
        role_id=role.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
async def test_instance(db_session):
    """Create test Oracle instance"""
    instance = Instance(
        name="test-oracle",
        host="localhost",
        port=1521,
        service_name="ORCL",
        username="oracle",
        password_encrypted="encrypted_pwd",
        is_active=True
    )
    db_session.add(instance)
    await db_session.commit()

    return instance


@pytest.fixture
async def auth_headers(test_user):
    """Create authorization headers"""
    token = create_access_token({
        "sub": test_user.username,
        "user_id": test_user.id
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_login_flow(client, test_user, db_session):
    """Test login endpoint and token generation"""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_metrics_overview(client, test_instance, auth_headers, db_session):
    """Test metrics overview endpoint"""
    # Create test metrics
    now = datetime.utcnow()
    for i in range(5):
        metric = Metric(
            instance_id=test_instance.id,
            metric_type="sessions",
            value=100 + i * 10,
            unit="count",
            timestamp=now - timedelta(minutes=i)
        )
        db_session.add(metric)
    await db_session.commit()

    response = client.get(
        f"/api/metrics/overview/{test_instance.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert len(data["metrics"]) > 0


@pytest.mark.asyncio
async def test_alert_rule_crud(client, test_instance, auth_headers, db_session):
    """Test alert rule creation, read, update, delete"""
    # Create alert rule
    rule_data = {
        "instance_id": test_instance.id,
        "name": "High Session Count",
        "metric_type": "sessions",
        "threshold": 500,
        "operator": "gt",
        "enabled": True
    }

    response = client.post(
        "/api/alerts/rules",
        json=rule_data,
        headers=auth_headers
    )

    assert response.status_code == 201
    rule = response.json()
    rule_id = rule["id"]

    # Read alert rule
    response = client.get(
        f"/api/alerts/rules/{rule_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "High Session Count"

    # Update alert rule
    response = client.put(
        f"/api/alerts/rules/{rule_id}",
        json={**rule_data, "threshold": 600},
        headers=auth_headers
    )
    assert response.status_code == 200

    # Delete alert rule
    response = client.delete(
        f"/api/alerts/rules/{rule_id}",
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_instance_management(client, auth_headers, db_session):
    """Test instance CRUD operations"""
    instance_data = {
        "name": "test-oracle-2",
        "host": "192.168.1.100",
        "port": 1521,
        "service_name": "ORCL2",
        "username": "oracle",
        "password": "oracle_password"
    }

    # Create instance
    response = client.post(
        "/api/instances",
        json=instance_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    instance = response.json()
    instance_id = instance["id"]

    # Get instance
    response = client.get(
        f"/api/instances/{instance_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test-oracle-2"

    # List instances
    response = client.get(
        "/api/instances",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Update instance
    response = client.put(
        f"/api/instances/{instance_id}",
        json={**instance_data, "host": "192.168.1.101"},
        headers=auth_headers
    )
    assert response.status_code == 200

    # Delete instance
    response = client.delete(
        f"/api/instances/{instance_id}",
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_analytics_endpoints(client, test_instance, auth_headers, db_session):
    """Test analytics endpoints"""
    # Create test metrics
    now = datetime.utcnow()
    for i in range(24):
        for metric_type in ["cpu_usage", "memory_usage"]:
            metric = Metric(
                instance_id=test_instance.id,
                metric_type=metric_type,
                value=50 + i * 2,
                unit="percent",
                timestamp=now - timedelta(hours=i)
            )
            db_session.add(metric)
    await db_session.commit()

    # Test trend endpoint
    response = client.get(
        f"/api/analytics/trend/{test_instance.id}",
        params={"metric_type": "cpu_usage"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "trend" in data

    # Test forecast endpoint
    response = client.get(
        f"/api/analytics/forecast/{test_instance.id}",
        params={"metric_type": "memory_usage"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "forecast" in response.json()


@pytest.mark.asyncio
async def test_authorization(client, test_user, test_instance):
    """Test authorization for protected endpoints"""
    # Request without auth header
    response = client.get(f"/api/metrics/overview/{test_instance.id}")
    assert response.status_code == 401

    # Request with invalid token
    response = client.get(
        f"/api/metrics/overview/{test_instance.id}",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh(client, test_user):
    """Test token refresh flow"""
    # Get initial tokens
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password"
    })

    tokens = response.json()
    refresh_token = tokens["refresh_token"]

    # Refresh token
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_alert_acknowledgment(client, test_instance, auth_headers, db_session):
    """Test alert acknowledgment workflow"""
    # Create alert history entry
    alert = AlertHistory(
        instance_id=test_instance.id,
        alert_type="session_limit",
        message="Session limit exceeded",
        severity="critical",
        acknowledged=False
    )
    db_session.add(alert)
    await db_session.commit()

    # Acknowledge alert
    response = client.post(
        f"/api/alerts/history/{alert.id}/acknowledge",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["acknowledged"] is True


@pytest.mark.asyncio
async def test_pagination(client, test_instance, auth_headers, db_session):
    """Test pagination on list endpoints"""
    # Create multiple metrics
    now = datetime.utcnow()
    for i in range(25):
        metric = Metric(
            instance_id=test_instance.id,
            metric_type="sessions",
            value=100 + i,
            unit="count",
            timestamp=now - timedelta(minutes=i)
        )
        db_session.add(metric)
    await db_session.commit()

    # Test pagination
    response = client.get(
        f"/api/metrics/history/{test_instance.id}",
        params={"page": 1, "per_page": 10},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25


@pytest.mark.asyncio
async def test_error_handling(client, auth_headers):
    """Test error handling for invalid requests"""
    # Test non-existent resource
    response = client.get(
        "/api/instances/999999",
        headers=auth_headers
    )
    assert response.status_code == 404

    # Test invalid metric type
    response = client.get(
        "/api/metrics/overview/1",
        params={"metric_type": "invalid"},
        headers=auth_headers
    )
    assert response.status_code == 400
