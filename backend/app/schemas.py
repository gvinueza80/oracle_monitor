"""Pydantic schemas for request/response validation"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


# Instance Schemas
class InstanceCreate(BaseModel):
    """Create instance request"""
    name: str = Field(..., min_length=1, max_length=255, description="Instance name")
    description: Optional[str] = Field(None, max_length=1000)
    host: str = Field(..., min_length=1, max_length=255, description="Oracle host")
    port: int = Field(default=1521, ge=1, le=65535)
    service_name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=255, description="Will be encrypted")
    ssl_enabled: bool = False
    connection_timeout: int = Field(default=30, ge=5, le=300)
    pool_min: int = Field(default=2, ge=1, le=50)
    pool_max: int = Field(default=10, ge=1, le=100)

    @field_validator('pool_min', 'pool_max')
    @classmethod
    def validate_pools(cls, v, info):
        if info.field_name == 'pool_min' and info.data.get('pool_max'):
            if v > info.data['pool_max']:
                raise ValueError('pool_min must be <= pool_max')
        return v


class InstanceUpdate(BaseModel):
    """Update instance request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    service_name: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=1, max_length=128)
    password: Optional[str] = Field(None, min_length=1, max_length=255)
    ssl_enabled: Optional[bool] = None
    connection_timeout: Optional[int] = Field(None, ge=5, le=300)
    pool_min: Optional[int] = Field(None, ge=1, le=50)
    pool_max: Optional[int] = Field(None, ge=1, le=100)
    enabled: Optional[bool] = None


class InstanceResponse(BaseModel):
    """Instance response"""
    id: UUID
    name: str
    description: Optional[str]
    host: str
    port: int
    service_name: str
    ssl_enabled: bool
    connection_timeout: int
    pool_min: int
    pool_max: int
    enabled: bool
    connection_status: Optional[str]
    last_connection_check: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstanceListResponse(BaseModel):
    """List instances response"""
    instances: List[InstanceResponse]
    total: int
    limit: int
    offset: int


# Metric Schemas
class MetricResponse(BaseModel):
    """Single metric data point"""
    metric_type: str
    metric_value: float
    metric_unit: Optional[str]
    collected_at: datetime
    tags: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class MetricsHistoryResponse(BaseModel):
    """Metrics history response"""
    metric_type: str
    data_points: List[MetricResponse]
    period_start: datetime
    period_end: datetime
    period_hours: int
    total_points: int


class OverviewMetricsResponse(BaseModel):
    """Dashboard overview metrics"""
    active_sessions: int
    locked_sessions: int
    tablespace_used_percent: float
    slow_queries_count: int
    critical_alerts: int
    warning_alerts: int
    instance_health_status: str  # healthy, degraded, critical
    last_update: datetime


# Session Schemas
class SessionResponse(BaseModel):
    """Active session details"""
    session_id: str
    serial_number: str
    user_id: str
    program: Optional[str]
    module: Optional[str]
    status: str
    logon_time: datetime
    last_call_et: Optional[float]
    memory_mb: Optional[float]
    cpu_time_sec: Optional[float]
    disk_reads: Optional[int]
    disk_writes: Optional[int]
    sql_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SessionsResponse(BaseModel):
    """List sessions response"""
    sessions: List[SessionResponse]
    total: int
    limit: int
    offset: int


# Lock Schemas
class LockResponse(BaseModel):
    """Lock details"""
    blocker_session_id: str
    blocker_serial: str
    blocked_session_id: str
    blocked_serial: str
    lock_type: Optional[str]
    object_owner: Optional[str]
    object_name: Optional[str]
    detected_at: datetime
    resolved_at: Optional[datetime]
    duration_sec: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class LocksResponse(BaseModel):
    """List locks response"""
    locks: List[LockResponse]
    blockers: List[str]  # blocker session IDs
    last_update: datetime


# Slow Query Schemas
class SlowQueryResponse(BaseModel):
    """Slow query details"""
    sql_id: str
    sql_text: str
    executions: int
    avg_duration_ms: float
    total_duration_sec: float
    cpu_time_sec: Optional[float]
    disk_reads: Optional[int]
    rows_processed: Optional[int]
    last_execution: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SlowQueriesResponse(BaseModel):
    """List slow queries response"""
    queries: List[SlowQueryResponse]
    count: int


# Tablespace Schemas
class TablespaceResponse(BaseModel):
    """Tablespace details"""
    tablespace_name: str
    total_size_mb: float
    free_space_mb: float
    used_percent: float


class TablespacesResponse(BaseModel):
    """List tablespaces response"""
    tablespaces: List[TablespaceResponse]
    total_size_gb: float
    used_size_gb: float
    total_count: int


# Alert Schemas
class AlertRuleCreate(BaseModel):
    """Create alert rule request"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metric_type: str = Field(..., regex="^[a-z_]+$")
    threshold: float = Field(..., gt=0)
    condition: str = Field(..., regex="^(gt|lt|eq|gte|lte)$")
    check_duration: int = Field(default=300, ge=10, le=3600)
    severity: str = Field(default="warning", regex="^(info|warning|critical)$")
    enabled: bool = True
    notifications: Optional[Dict[str, Any]] = None
    auto_remediation_enabled: bool = False
    auto_remediation_action: Optional[str] = None


class AlertRuleUpdate(BaseModel):
    """Update alert rule request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    threshold: Optional[float] = Field(None, gt=0)
    condition: Optional[str] = Field(None, regex="^(gt|lt|eq|gte|lte)$")
    severity: Optional[str] = Field(None, regex="^(info|warning|critical)$")
    enabled: Optional[bool] = None
    notifications: Optional[Dict[str, Any]] = None


class AlertRuleResponse(BaseModel):
    """Alert rule response"""
    id: UUID
    instance_id: UUID
    name: str
    description: Optional[str]
    metric_type: str
    threshold: float
    condition: str
    check_duration: int
    severity: str
    enabled: bool
    notifications: Optional[Dict[str, Any]]
    suppress_until: Optional[datetime]
    auto_remediation_enabled: bool
    auto_remediation_action: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRulesResponse(BaseModel):
    """List alert rules response"""
    rules: List[AlertRuleResponse]
    count: int


class AlertHistoryResponse(BaseModel):
    """Alert history entry"""
    id: int
    rule_id: UUID
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    metric_value: Optional[float]
    metric_unit: Optional[str]
    message: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)


class AlertsResponse(BaseModel):
    """List alerts response"""
    alerts: List[AlertHistoryResponse]
    total: int
    limit: int
    offset: int


class AlertAcknowledgeRequest(BaseModel):
    """Acknowledge alert request"""
    message: Optional[str] = None


class AlertResolveRequest(BaseModel):
    """Resolve alert request"""
    message: Optional[str] = None


# User Schemas
class UserCreate(BaseModel):
    """Create user request"""
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=255)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Update user request"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response"""
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UsersResponse(BaseModel):
    """List users response"""
    users: List[UserResponse]
    total: int


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# WebSocket Schemas
class MetricUpdateMessage(BaseModel):
    """Real-time metric update via WebSocket"""
    type: str = "metric_update"
    instance_id: str
    metric_type: str
    metric_value: float
    collected_at: datetime
    tags: Optional[Dict[str, Any]] = None


class AlertNotificationMessage(BaseModel):
    """Alert notification via WebSocket"""
    type: str = "alert_triggered"
    alert_id: int
    rule_id: str
    rule_name: str
    severity: str
    metric_value: float
    triggered_at: datetime
    message: Optional[str] = None


class SessionUpdateMessage(BaseModel):
    """Session change notification"""
    type: str = "session_update"
    instance_id: str
    action: str  # new, updated, killed
    session_id: str
    user_id: str
    timestamp: datetime
