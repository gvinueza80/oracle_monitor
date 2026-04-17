"""SQLAlchemy ORM models"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary,
    String, Text, UniqueConstraint, Index, DECIMAL, BigInteger, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from db import Base
import enum


class Instance(Base):
    """Oracle database instance configuration"""
    __tablename__ = "instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Connection details (encrypted in app layer)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=1521)
    service_name = Column(String(255), nullable=False)
    username = Column(String(128), nullable=False)
    password_encrypted = Column(LargeBinary, nullable=False)

    # Configuration
    ssl_enabled = Column(Boolean, default=False)
    connection_timeout = Column(Integer, default=30)
    pool_min = Column(Integer, default=2)
    pool_max = Column(Integer, default=10)

    # Status
    enabled = Column(Boolean, default=True, index=True)
    last_connection_check = Column(DateTime(timezone=True))
    connection_status = Column(String(20))  # connected, failed, unknown

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    metrics = relationship("Metric", back_populates="instance", cascade="all, delete-orphan")
    active_sessions = relationship("ActiveSession", back_populates="instance")
    locks = relationship("Lock", back_populates="instance")
    slow_queries = relationship("SlowQuery", back_populates="instance")
    alert_rules = relationship("AlertRule", back_populates="instance")

    __table_args__ = (
        Index('idx_instances_enabled_created', 'enabled', 'created_at'),
    )


class User(Base):
    """System users"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(128), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)

    # MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index('idx_users_active_created', 'is_active', 'created_at'),
    )


class Role(Base):
    """User roles for RBAC"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Permissions as JSON (stored as strings like 'metrics:read', 'alerts:manage')
    permissions = Column(ARRAY(String), default=[])

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")


class UserRole(Base):
    """User to Role mapping"""
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Metric(Base):
    """Time-series metrics (partitioned by instance and date)"""
    __tablename__ = "metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    metric_type = Column(String(50), nullable=False, index=True)  # cpu_usage, memory, sessions, etc.
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))  # percent, MB, count, ms

    # Tags for filtering (session_id, user_id, program, etc.)
    tags = Column(JSON)

    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationship
    instance = relationship("Instance", back_populates="metrics")

    __table_args__ = (
        Index('idx_metrics_instance_type_collected', 'instance_id', 'metric_type', 'collected_at'),
        Index('idx_metrics_collected_desc', 'collected_at', 'instance_id'),
    )


class ActiveSession(Base):
    """Current active sessions snapshot"""
    __tablename__ = "active_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    session_id = Column(String(50), nullable=False)
    serial_number = Column(String(50), nullable=False)
    user_id = Column(String(30), nullable=False)
    program = Column(String(100))
    module = Column(String(100))
    status = Column(String(20), nullable=False)  # ACTIVE, IDLE, KILLED, etc.

    # Timing
    logon_time = Column(DateTime(timezone=True), nullable=False)
    last_call_et = Column(Float)  # seconds

    # Resource usage
    memory_mb = Column(Float)
    cpu_time_sec = Column(Float)
    disk_reads = Column(BigInteger)
    disk_writes = Column(BigInteger)
    rows_processed = Column(BigInteger)

    # Current activity
    sql_id = Column(String(13))
    current_sql = Column(Text)

    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationship
    instance = relationship("Instance", back_populates="active_sessions")

    __table_args__ = (
        UniqueConstraint('instance_id', 'session_id', 'serial_number', 'collected_at', name='uc_session_snapshot'),
        Index('idx_sessions_instance_user', 'instance_id', 'user_id'),
        Index('idx_sessions_instance_status', 'instance_id', 'status'),
    )


class Lock(Base):
    """Database locks and blocking relationships"""
    __tablename__ = "locks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    blocker_session_id = Column(String(50), nullable=False)
    blocker_serial = Column(String(50), nullable=False)
    blocked_session_id = Column(String(50), nullable=False)
    blocked_serial = Column(String(50), nullable=False)

    lock_type = Column(String(30))
    object_owner = Column(String(30))
    object_name = Column(String(100))

    # Timing
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    duration_sec = Column(Float)

    # Relationship
    instance = relationship("Instance", back_populates="locks")

    __table_args__ = (
        Index('idx_locks_instance_detected', 'instance_id', 'detected_at'),
        Index('idx_locks_unresolved', 'instance_id', 'resolved_at'),
    )


class SlowQuery(Base):
    """Slow query tracking from AWR"""
    __tablename__ = "slow_queries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    sql_id = Column(String(13), nullable=False, index=True)
    sql_hash = Column(String(16), index=True)
    sql_text = Column(Text, nullable=False)

    # Statistics
    executions = Column(BigInteger)
    avg_duration_ms = Column(Float)
    total_duration_sec = Column(Float)
    min_duration_ms = Column(Float)
    max_duration_ms = Column(Float)

    cpu_time_sec = Column(Float)
    disk_reads = Column(BigInteger)
    buffer_gets = Column(BigInteger)
    rows_processed = Column(BigInteger)

    last_execution = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationship
    instance = relationship("Instance", back_populates="slow_queries")

    __table_args__ = (
        Index('idx_slow_queries_instance_duration', 'instance_id', 'avg_duration_ms'),
        Index('idx_slow_queries_instance_collected', 'instance_id', 'collected_at'),
    )


class AlertRuleSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertRule(Base):
    """Alert rule definitions"""
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    metric_type = Column(String(50), nullable=False)  # cpu_usage, memory, locks, etc.

    # Condition evaluation
    threshold = Column(DECIMAL(10, 2), nullable=False)
    condition = Column(String(20), nullable=False)  # gt, lt, eq, gte, lte
    check_duration = Column(Integer, default=300)  # seconds

    severity = Column(SQLEnum(AlertRuleSeverity), default=AlertRuleSeverity.WARNING)
    enabled = Column(Boolean, default=True, index=True)

    # Notifications
    notifications = Column(JSON)  # {channels: [{type: email, recipients: [...]}]}

    # Suppression
    suppress_until = Column(DateTime(timezone=True))

    # Auto-remediation
    auto_remediation_enabled = Column(Boolean, default=False)
    auto_remediation_action = Column(String(50))  # stop_service, increase_memory, etc.

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationship
    instance = relationship("Instance", back_populates="alert_rules")

    __table_args__ = (
        Index('idx_alert_rules_instance_enabled', 'instance_id', 'enabled'),
    )


class AlertHistory(Base):
    """Alert trigger history"""
    __tablename__ = "alert_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)

    triggered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    resolved_at = Column(DateTime(timezone=True))
    suppressed_until = Column(DateTime(timezone=True))

    metric_value = Column(Float)
    metric_unit = Column(String(20))

    message = Column(Text)
    status = Column(String(20), default="triggered")  # triggered, acknowledged, resolved

    __table_args__ = (
        Index('idx_alert_history_rule_triggered', 'rule_id', 'triggered_at'),
        Index('idx_alert_history_status_triggered', 'status', 'triggered_at'),
    )


class AuditLog(Base):
    """Audit trail for compliance"""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    action = Column(String(50), nullable=False)  # create, update, delete, query, kill_session
    resource_type = Column(String(50), nullable=False)  # session, instance, rule, user
    resource_id = Column(String(255), nullable=False)

    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_audit_logs_user_created', 'user_id', 'created_at'),
        Index('idx_audit_logs_action_created', 'action', 'created_at'),
    )
