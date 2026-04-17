# Oracle Database Monitoring System - Technical Specification

## 1. System Architecture

### 1.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
├──────────────────────────┬──────────────────────────────────────┤
│   Web Dashboard (React)  │    Mobile App (Flutter)              │
│   - TypeScript/Tailwind  │    - Dart + Riverpod                │
│   - Redux State Mgmt     │    - Hive Local Storage             │
└──────┬───────────────────┴──────────────────────┬────────────────┘
       │ HTTPS/WSS                                │ HTTPS/gRPC
       │                                          │
┌──────▼──────────────────────────────────────────▼────────────────┐
│                    API GATEWAY LAYER                             │
│              (FastAPI + Authentication)                          │
├─────────────────────────────────────────────────────────────────┤
│ - JWT Token Validation                                          │
│ - Role-Based Access Control (RBAC)                             │
│ - Rate Limiting & Request Logging                              │
│ - WebSocket Handler (real-time updates)                        │
└─┬───────────────────────────────┬──────────────────┬───────────┘
  │                               │                  │
  ▼                               ▼                  ▼
┌─────────────────┐      ┌──────────────────┐   ┌────────────────┐
│  Metrics API    │      │  Alerts API      │   │  Config API    │
│  - Active Data  │      │  - Rules Engine  │   │  - Instances   │
│  - Historical   │      │  - Notifications │   │  - Users/Roles │
└────────┬────────┘      └────────┬─────────┘   └────────┬───────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
        ▼                                                   ▼
   ┌──────────────┐                              ┌─────────────────┐
   │  Data Layer  │                              │  Cache Layer    │
   │              │                              │                 │
   │ PostgreSQL   │◄──────────────────────────►  │     Redis       │
   │ (Metrics,    │      Async Sync              │  (Real-time     │
   │  Logs,       │                              │   Metrics)      │
   │  Audit)      │                              │                 │
   └──────────────┘                              └─────────────────┘
        ▲
        │
        │ Collector Service
        │ (Async Jobs via Celery)
        │
┌───────┴─────────────────────────────────────────────────────────┐
│             ORACLE DATABASE CONNECTION LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│  Credential Vault (HashiCorp Vault)                             │
│       │                    │                    │                │
│       ▼                    ▼                    ▼                │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐         │
│  │Instance1│          │Instance2│          │Instance-N│        │
│  │(Prod)   │          │(Dev)    │          │(UAT)     │        │
│  └─────────┘          └─────────┘          └─────────┘         │
│                                                                  │
│  Data Queries:                                                  │
│  - v$session, v$sysstat, v$system_event (Active)               │
│  - dba_tablespaces, dba_segments (Storage)                      │
│  - v$lock, v$locked_object (Locks)                             │
│  - v$sql, gv$sql_plan (Query Performance)                      │
│  - v$osstat, gv$sysmetric (System Metrics)                     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Breakdown

#### Backend Services (FastAPI/Python)

**API Service** (`backend/app/main.py`)
- REST endpoints for metrics, alerts, configuration
- WebSocket endpoint for real-time updates
- Authentication middleware (JWT)
- RBAC middleware
- Error handling and validation

**Data Collector** (`backend/collector/`)
- Scheduled tasks via Celery for polling Oracle
- Metric transformation and normalization
- Data persistence to PostgreSQL and Redis
- Error handling with retry logic

**Alert Engine** (`backend/alerts/`)
- Rule evaluation against real-time metrics
- Notification routing (in-app, email, push)
- Escalation policies
- Acknowledgment and suppression

**Database Models** (`backend/models/`)
- Instance configuration
- User and role definitions
- Metrics schema (normalized)
- Alert definitions and history
- Audit logs

#### Frontend (Django + React)

**Django Backend** (`web/`)
- Serves React SPA static files
- Session management
- Server-side rendering for SEO (optional)

**React Application** (`web/frontend/`)
- Dashboard components (overview, metrics detail, alerts)
- Configuration management UI
- User admin panel
- Real-time metrics display with charts

#### Mobile App (Flutter)

**Dart Application** (`mobile/`)
- Dashboard screen (summary metrics)
- Alerts management screen
- Detail screens for drill-down
- Settings and configuration
- Local offline caching with Hive

---

## 2. Data Collection & Integration

### 2.1 Oracle Connection Strategy

```python
# backend/db/oracle_client.py (conceptual)

class OracleMetricsCollector:
    def __init__(self, instance_config):
        self.pool = cx_Oracle.SessionPool(
            user=instance_config.username,
            password=instance_config.password,
            dsn=instance_config.dsn,
            min=2, max=10, increment=1,
            threaded=True
        )
    
    async def collect_metrics(self):
        # High-frequency (5-10s): locks, active sessions, slow queries
        # Medium (30s): CPU, memory, connections
        # Low (5min): tablespace, archive logs, schema growth
        pass
```

### 2.2 Metric Collection Strategy

| Metric Type | Query | Frequency | Priority | Retention |
|------------|-------|-----------|----------|-----------|
| **Active Sessions** | v$session | 10s | Critical | 7 days |
| **Locks & Blocks** | v$lock, v$locked_object | 5s | Critical | 24 hours |
| **Slow Queries** | v$sql, dba_hist_sqlstat | 30s | High | 30 days |
| **Tablespace Usage** | dba_tablespaces, dba_segments | 5m | High | 90 days |
| **CPU Usage** | v$sysstat, gv$sysmetric | 30s | Medium | 30 days |
| **Memory Utilization** | v$sga, v$sga_dynamic_components | 30s | Medium | 30 days |
| **Connection Health** | v$session COUNT | 10s | Critical | 7 days |
| **System Events** | v$system_event | 5m | Low | 30 days |
| **Database Activity** | v$log, v$logfile | 5m | Medium | 90 days |

### 2.3 Polling Architecture

**Celery Beat Schedule** (configurable):
```python
from celery.schedules import schedule

CELERY_BEAT_SCHEDULE = {
    'collect-critical-metrics': {
        'task': 'collector.tasks.collect_critical_metrics',
        'schedule': schedule(run_every=10),  # 10 seconds
    },
    'collect-standard-metrics': {
        'task': 'collector.tasks.collect_standard_metrics',
        'schedule': schedule(run_every=30),  # 30 seconds
    },
    'collect-historical-metrics': {
        'task': 'collector.tasks.collect_historical_metrics',
        'schedule': schedule(run_every=300),  # 5 minutes
    },
}
```

### 2.4 Multi-Instance Support

- **Instance Registry**: PostgreSQL table storing connection configs
- **Per-Instance Collectors**: Separate Celery workers or task routing
- **Credential Management**: Vault integration for secure storage
- **Namespace Isolation**: All metrics tagged with instance_id

---

## 3. User Interface Design

### 3.1 Web Dashboard Information Architecture

```
Dashboard Home
├── Overview Panel (4 KPIs)
│   ├── Active Sessions
│   ├── Locked Objects
│   ├── Tablespace Usage (%)
│   └── Slow Queries Count
├── Real-time Alerts (List)
│   ├── Critical
│   ├── Warning
│   └── Info
└── Quick Actions
    ├── View Active Sessions
    ├── View Locks
    └── Refresh Metrics

Sessions Detail View
├── Active Sessions Table
│   ├── Session ID, User, Status, Duration
│   ├── CPU Time, Memory, I/O
│   ├── Filter/Search by User/Program
│   └── Action: Kill Session, Trace Session
├── Session Breakdown by User
├── Session Breakdown by Program
└── Time-series Charts

Locks & Blocking View
├── Lock Matrix (blocker → blocked)
├── Lock Details Panel
│   ├── Lock Type, Held Duration
│   ├── Affected Objects
│   └── Action: Kill Blocking Session
├── Historical Lock Trends
└── Automatic Lock Resolution (optional)

Tablespace Management
├── Capacity Overview (Pie Chart)
├── Top 10 Objects by Size
├── Growth Trend (30/90 days)
├── Datafile Details
│   ├── Location, Size, Auto-extend
│   └── Action: Add Datafile
└── Alert Configuration

Performance Analysis
├── Slow Queries (Top 10)
│   ├── SQL Text, Executions, Avg Duration
│   ├── Execution Plan
│   └── Index Suggestions
├── Wait Events by Category
├── CPU Top Consumers
├── I/O Top Consumers
└── Time-series Performance Charts

System Metrics
├── CPU Usage (Historical Graph)
├── Memory Utilization
├── Disk I/O (Read/Write)
├── Network Activity
└── Database Size Growth

Configuration
├── Instance Management
│   ├── Add/Edit/Remove Instances
│   ├── Connection Testing
│   └── Credentials
├── User Management (Admin Only)
│   ├── User Roles, Permissions
│   └── Audit Trail
└── Alert Rules Configuration

Alerts Management
├── All Alerts (Filtered by Status/Severity)
├── Alert Details
│   ├── History, Related Metrics
│   └── Acknowledge/Suppress/Resolve
├── Alert Rules (Create/Edit)
│   ├── Condition Builder
│   ├── Severity Level
│   ├── Notification Method
│   └── Auto-remediation Action
└── Notification Preferences
    ├── Email, SMS, Slack, PagerDuty
    └── Quiet Hours
```

### 3.2 Mobile Dashboard (Flutter)

```
Home Screen (Scrollable)
├── Status Card (Top)
│   ├── Overall Health Status
│   ├── Critical Alert Count (Red Badge)
│   └── Last Refresh Time
├── Quick Stats (Grid, 2 columns)
│   ├── Active Sessions (Tap to see list)
│   ├── Locks (Tap to see details)
│   ├── Tablespace %
│   └── Slow Queries
├── Recent Alerts (Scrollable List)
│   ├── Alert Icon, Type, Time
│   ├── Swipe to Acknowledge
│   └── Tap for Details
└── Navigation Tabs
    ├── Home (current)
    ├── Sessions
    ├── Alerts
    ├── Performance
    └── Settings

Sessions Screen
├── Search/Filter Bar
├── Session List (Pull-to-refresh)
│   ├── User, Session ID, Duration
│   ├── Status Indicator (running/idle/dead)
│   └── Tap for Details
├── Session Details Modal
│   ├── Full Info, CPU, Memory, I/O
│   ├── SQL Being Executed (if any)
│   └── Kill Session Button (long-press confirm)
└── Session Breakdown Charts (via carousel)

Alerts Screen
├── Filter Tabs (All, Critical, Warning, Info)
├── Alert List
│   ├── Alert Type Icon, Title, Time
│   ├── Severity Color Coding
│   └── Tap for Details
├── Alert Details Modal
│   ├── Full Description, Related Metric
│   ├── Trending Chart
│   ├── Acknowledge/Suppress Buttons
│   └── Related Actions (e.g., Kill Session)
└── Alert Rules (Settings)
    ├── List of Active Rules
    └── Create/Edit/Delete Rule

Performance Screen
├── Metric Selector (Dropdown)
├── Real-time Chart (Line/Bar)
│   ├── 1-hour, 24-hour, 7-day views
│   └── Pinch-to-zoom
├── Top Items (CPU, I/O, Memory)
│   └── Tap for Details
└── Slow Queries
    ├── Top 5 Queries (SQL text truncated)
    └── Tap for Full Execution Plan

Settings Screen
├── Instance Selection (if multiple)
├── Notification Preferences
│   ├── Push Notifications Toggle
│   ├── Quiet Hours
│   └── Notification Types
├── Auto-refresh Interval
├── Offline Mode Toggle (uses local cache)
├── Logout
└── About & Version
```

### 3.3 Drill-Down Navigation Pattern

- **Overview → Detail**: Click metric card opens detailed view with filters
- **Alert → Source Metric**: Click alert opens related metric dashboard
- **Session → Lock Details**: Click session in lock view shows blocker relationship
- **Slow Query → Execution Plan**: Click query opens EXPLAIN PLAN visualization
- **Breadcrumb Navigation**: Always show path for back-navigation

### 3.4 Responsive Design

| Device | Breakpoint | Layout |
|--------|-----------|--------|
| Mobile Portrait | <600px | Single column, stacked cards |
| Mobile Landscape | 600-900px | Two-column layout |
| Tablet | 900-1200px | Three-column dashboard |
| Desktop | >1200px | Full dashboard with sidebar |

---

## 4. Alerting & Notifications

### 4.1 Alert Thresholds (Configurable)

```python
# backend/alerts/thresholds.py

ALERT_THRESHOLDS = {
    'cpu_usage': {
        'warning': 70,      # %
        'critical': 85,     # %
        'check_duration': 300,  # seconds
    },
    'memory_utilization': {
        'warning': 80,      # %
        'critical': 95,     # %
    },
    'tablespace_usage': {
        'warning': 80,      # %
        'critical': 95,     # %
        'per_tablespace': True,
    },
    'locked_sessions': {
        'warning': 1,       # count > 1 minute
        'critical': 3,      # count > 5 minutes
    },
    'slow_queries': {
        'warning': 5,       # queries > 5s
        'critical': 10,     # queries > 30s
        'threshold_duration': 30,  # seconds
    },
    'connection_errors': {
        'warning': 5,       # errors per minute
        'critical': 10,     # errors per minute
    },
    'active_sessions': {
        'warning': 200,     # count
        'critical': 300,    # count
    },
    'archive_log_warning': {
        'warning': 90,      # % of destination full
        'critical': 95,     # % of destination full
    },
}
```

### 4.2 Notification Delivery

**Channels**:
- **In-App**: Real-time list with persistence
- **Email**: Configurable recipients, digest or immediate
- **Push Notification**: Mobile app (FCM/APNs)
- **Slack Integration**: Channel posting with rich formatting
- **PagerDuty**: Incident creation for critical alerts
- **Custom Webhook**: Generic HTTP POST to user-defined URL

**Configuration Example**:
```python
# backend/models/alert_rule.py

class AlertRule(Model):
    name: str
    metric_type: str  # cpu_usage, memory, etc.
    threshold: float
    severity: str  # warning, critical
    enabled: bool
    condition: str  # "greater_than", "less_than", "equals"
    check_duration: int  # seconds
    notifications:
        - channel: email
          recipients: ["dba@company.com"]
          include_digest: true
        - channel: slack
          webhook_url: "https://hooks.slack.com/..."
        - channel: pagerduty
          service_key: "xxx"
          escalation_policy: "primary-on-call"
    auto_remediation: optional  # stop service, increase memory, etc.
    suppress_until: datetime  # snooze alerts
    created_by: str
    created_at: datetime
```

### 4.3 Alert State Management

```
┌─────────────┐
│   CREATED   │ (New alert detected)
└──────┬──────┘
       │
       ▼
┌──────────────┐
│   TRIGGERED  │◄──────┐ (Condition re-met after clear)
└──────┬───────┘       │
       │               │
       ▼               │
┌──────────────┐       │
│ ACKNOWLEDGED │       │ (User acknowledges)
└──────┬───────┘       │
       │               │
   (no change)    (condition still true)
       │               │
       ▼               │
┌──────────────┐       │
│   RESOLVED   │───────┘
└──────────────┘ (Condition cleared)
```

---

## 5. Data Persistence & Storage

### 5.1 PostgreSQL Schema

**Metrics Table** (time-series):
```sql
-- Partitioned by instance_id and date
CREATE TABLE metrics (
    id BIGSERIAL PRIMARY KEY,
    instance_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- cpu_usage, memory, etc.
    metric_value NUMERIC NOT NULL,
    tags JSONB,  -- {session_id, user, program, etc.}
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_instance_collected 
    ON metrics(instance_id, collected_at DESC);
CREATE INDEX idx_metrics_type_collected 
    ON metrics(metric_type, collected_at DESC);

-- Partition by date
CREATE TABLE metrics_2024_01 PARTITION OF metrics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

**Active Sessions Snapshot**:
```sql
CREATE TABLE active_sessions (
    id BIGSERIAL PRIMARY KEY,
    instance_id UUID NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(30) NOT NULL,
    program VARCHAR(100),
    status VARCHAR(20),  -- ACTIVE, IDLE
    logon_time TIMESTAMP NOT NULL,
    last_call_et NUMERIC,  -- CPU time
    memory_mb NUMERIC,
    cpu_time_sec NUMERIC,
    disk_reads BIGINT,
    disk_writes BIGINT,
    collected_at TIMESTAMP NOT NULL,
    
    UNIQUE(instance_id, session_id, collected_at)
);

CREATE INDEX idx_sessions_instance_user 
    ON active_sessions(instance_id, user_id);
```

**Locks**:
```sql
CREATE TABLE locks (
    id BIGSERIAL PRIMARY KEY,
    instance_id UUID NOT NULL,
    blocker_session_id VARCHAR(50) NOT NULL,
    blocked_session_id VARCHAR(50) NOT NULL,
    lock_type VARCHAR(30),
    object_name VARCHAR(100),
    detected_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    duration_sec NUMERIC,
    
    INDEX idx_locks_instance_detected ON (instance_id, detected_at)
);
```

**Slow Queries**:
```sql
CREATE TABLE slow_queries (
    id BIGSERIAL PRIMARY KEY,
    instance_id UUID NOT NULL,
    sql_id VARCHAR(13) NOT NULL,
    sql_text TEXT NOT NULL,
    executions BIGINT,
    avg_duration_ms NUMERIC,
    total_duration_sec NUMERIC,
    last_execution TIMESTAMP,
    cpu_time_sec NUMERIC,
    disk_reads BIGINT,
    rows_processed BIGINT,
    collected_at TIMESTAMP NOT NULL,
    
    INDEX idx_slow_queries_instance_duration 
        ON (instance_id, avg_duration_ms DESC)
);
```

**Alert Rules & History**:
```sql
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY,
    instance_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    threshold NUMERIC NOT NULL,
    condition VARCHAR(20),  -- gt, lt, eq
    severity VARCHAR(20),  -- warning, critical
    enabled BOOLEAN DEFAULT TRUE,
    notifications JSONB,  -- channels, recipients, webhooks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL
);

CREATE TABLE alert_history (
    id BIGSERIAL PRIMARY KEY,
    rule_id UUID NOT NULL REFERENCES alert_rules(id),
    triggered_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    acknowledged_by UUID,
    resolved_at TIMESTAMP,
    metric_value NUMERIC,
    message TEXT,
    
    INDEX idx_alerts_rule_triggered ON (rule_id, triggered_at DESC)
);
```

**Audit Log**:
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    action VARCHAR(50),  -- create, update, delete, query, kill_session
    resource_type VARCHAR(50),  -- session, instance, rule
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_created ON audit_logs(user_id, created_at DESC);
```

### 5.2 Data Retention Policy

| Data Type | Retention | Aggregation After |
|-----------|-----------|-------------------|
| Raw Metrics | 7 days | - |
| Hourly Metrics | 90 days | After 7 days |
| Daily Metrics | 2 years | After 90 days |
| Alert History | 1 year | - |
| Audit Logs | 2 years | - |
| Session Snapshots | 30 days | - |
| Slow Query Stats | 90 days | - |

**Cleanup Queries** (via Celery Beat):
```python
@periodic_task(run_every=crontab(hour=2, minute=0))
def cleanup_old_metrics():
    cutoff = timezone.now() - timedelta(days=7)
    Metrics.objects.filter(created_at__lt=cutoff).delete()
    
@periodic_task(run_every=crontab(hour=3, minute=0))
def aggregate_hourly_metrics():
    # Aggregate raw data to hourly buckets
    pass
```

---

## 6. Performance & Scalability

### 6.1 Response Time Targets

| Endpoint | Target | Notes |
|----------|--------|-------|
| GET /metrics/overview | <500ms | Cached, 30s TTL |
| GET /sessions | <1s | Paginated, 10s polling |
| GET /locks | <500ms | Critical, 5s polling |
| GET /slow-queries | <1s | Sorted by duration |
| WebSocket connect | <100ms | Real-time metrics push |
| POST /alert-rule | <500ms | Validation + DB write |

### 6.2 Caching Strategy

**Redis Layers**:
```
Layer 1: Real-time Metrics (5-30s TTL)
  - Key: metrics:{instance_id}:{metric_type}
  - Value: Latest metric value + timestamp
  
Layer 2: Session Snapshots (10s TTL)
  - Key: sessions:{instance_id}
  - Value: Serialized session list JSON
  
Layer 3: Lock Matrix (5s TTL)
  - Key: locks:{instance_id}
  - Value: Blocker/blocked relationships
  
Layer 4: Computed Aggregates (5m TTL)
  - Key: stats:{instance_id}:daily:{date}
  - Value: Pre-computed daily summary
  
Layer 5: Query Plans (1h TTL)
  - Key: explain_plan:{sql_id}
  - Value: EXPLAIN PLAN output
```

**Cache Invalidation**:
- Time-based: TTL expiration
- Event-based: Collection job invalidates on data refresh
- Manual: Admin trigger to clear instance cache

### 6.3 Database Optimization

**Query Optimization**:
- Composite indexes on commonly filtered columns
- Partitioning metrics tables by date and instance
- Materialized views for complex aggregations
- Connection pooling (10-50 connections per instance)

**Oracle-side**:
```sql
-- Enable fast refresh for key queries
CREATE MATERIALIZED VIEW mv_active_sessions_summary AS
SELECT instance_id, COUNT(*) as count, SUM(memory_mb) as total_memory
FROM active_sessions
WHERE collected_at > TRUNC(SYSDATE)
GROUP BY instance_id;

-- Archive historical data monthly
CREATE PARTITION sessions_2024_01 VALUES LESS THAN ('2024-02-01');
```

### 6.4 Horizontal Scaling

**Components**:
- **API Servers**: Stateless, scale via load balancer (Nginx)
- **Celery Workers**: Scale per instance (1 worker per 10 instances)
- **Redis Cluster**: 3+ nodes for replication
- **PostgreSQL**: Primary + replicas (read-only for metrics)

**Load Distribution**:
```
  Client Requests
        │
        ▼
  Load Balancer (Nginx)
    │      │      │
    ▼      ▼      ▼
  API-1  API-2  API-3  (stateless FastAPI instances)
    │      │      │
    └──────┴──────┘
         │
         ▼
    PostgreSQL (Primary)
         │
    ┌────┴────┐
    ▼         ▼
  Replica  Replica (read-only)
```

---

## 7. Production-Ready Implementation

### 7.1 Error Handling Strategy

**Backend Error Classes**:
```python
# backend/errors.py

class OracleConnectionError(Exception):
    """Failed to connect to Oracle database"""
    pass

class MetricCollectionError(Exception):
    """Error during metric collection"""
    pass

class ValidationError(Exception):
    """Invalid input parameters"""
    pass

class AuthenticationError(Exception):
    """Auth token invalid/expired"""
    pass

class PermissionError(Exception):
    """User lacks required role"""
    pass

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": request.state.request_id}
    )
```

**Retry Logic**:
```python
# backend/collector/retry.py

async def collect_with_retry(instance_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await collect_metrics(instance_id)
        except OracleConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # exponential backoff
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Max retries exceeded for {instance_id}")
                raise
```

### 7.2 Input Validation

**Framework**: Pydantic for API request validation
```python
# backend/models/api_schemas.py

class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    metric_type: str = Field(..., regex="^[a-z_]+$")
    threshold: float = Field(..., gt=0, le=100)
    severity: Literal['warning', 'critical']
    condition: Literal['gt', 'lt', 'eq']
    
    @validator('name')
    def sanitize_name(cls, v):
        # Prevent SQL injection-like patterns
        return v.strip()
```

### 7.3 Logging & Monitoring

**Structured Logging**:
```python
# backend/logging_config.py

import logging
import json
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)

class StructuredLogger:
    @staticmethod
    def log_event(event_type, severity, message, **context):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'message': message,
            **context
        }
        logger.info(json.dumps(log_data))

# Usage
StructuredLogger.log_event(
    'metric_collection',
    'error',
    'Failed to collect CPU metrics',
    instance_id='prod-db-01',
    error='connection timeout'
)
```

**Prometheus Metrics**:
```python
# backend/metrics.py

from prometheus_client import Counter, Histogram, Gauge

metric_collection_errors = Counter(
    'metric_collection_errors_total',
    'Total metric collection errors',
    ['instance_id', 'metric_type']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method', 'status']
)

active_sessions = Gauge(
    'oracle_active_sessions',
    'Active sessions count',
    ['instance_id']
)
```

### 7.4 Testing Strategy

**Unit Tests** (pytest):
```python
# backend/tests/test_alert_rule_engine.py

import pytest
from alerts.engine import RuleEngine

@pytest.fixture
def rule_engine():
    return RuleEngine()

def test_cpu_threshold_alert(rule_engine):
    rule = AlertRule(
        metric_type='cpu_usage',
        threshold=80,
        condition='gt'
    )
    triggered = rule_engine.evaluate(rule, metric_value=85)
    assert triggered is True
    
def test_cpu_no_alert_below_threshold(rule_engine):
    rule = AlertRule(metric_type='cpu_usage', threshold=80, condition='gt')
    triggered = rule_engine.evaluate(rule, metric_value=75)
    assert triggered is False
```

**Integration Tests** (Docker Compose):
```python
# backend/tests/integration/test_oracle_collection.py

@pytest.mark.integration
async def test_collect_active_sessions(oracle_testdb):
    collector = OracleCollector(oracle_testdb.connection_string)
    sessions = await collector.collect_active_sessions()
    
    assert len(sessions) > 0
    assert 'session_id' in sessions[0]
    assert 'user_id' in sessions[0]
```

**E2E Tests** (Playwright/API):
```python
# web/tests/e2e/test_dashboard.spec.ts

import { test, expect } from '@playwright/test';

test('load dashboard and verify metrics display', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForSelector('[data-testid="overview-card"]');
    
    const sessionCount = await page.locator('[data-testid="session-count"]').textContent();
    expect(sessionCount).toMatch(/^\d+$/);
});
```

### 7.5 API Documentation

**OpenAPI/Swagger** (auto-generated by FastAPI):
```python
# backend/app/main.py

app = FastAPI(
    title="Oracle Monitoring API",
    description="Real-time Oracle database monitoring",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

@app.get("/metrics/{metric_type}", tags=["Metrics"])
async def get_metric(
    metric_type: str = Query(..., description="Type of metric to fetch"),
    instance_id: UUID = Query(..., description="Oracle instance ID"),
    hours: int = Query(24, ge=1, le=730, description="Historical hours to return")
) -> MetricsResponse:
    """
    Fetch metrics for a specific type.
    
    Returns paginated metric data with optional aggregation.
    """
    pass
```

### 7.6 Deployment & DevOps

**Docker Compose** (local development):
```yaml
# docker-compose.yml

version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/oracle_monitor
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
      
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: oracle_monitor
      POSTGRES_PASSWORD: dev_password
    volumes:
      - pgdata:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    
  celery:
    build: ./backend
    command: celery -A collector.tasks worker -l info
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/oracle_monitor
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
      
  celery-beat:
    build: ./backend
    command: celery -A collector.tasks beat -l info
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/oracle_monitor
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis

volumes:
  pgdata:
```

**Kubernetes Deployment** (production):
```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: oracle-monitor-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: oracle-monitor
  template:
    metadata:
      labels:
        app: oracle-monitor
    spec:
      containers:
      - name: api
        image: oracle-monitor:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          value: redis://redis-service:6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 8. Implementation Roadmap

### Phase 1: Core Backend (Weeks 1-3)
- [ ] FastAPI project scaffold
- [ ] PostgreSQL schema design and migration setup
- [ ] Oracle client library and connection pooling
- [ ] Basic metric collectors (5 core metrics)
- [ ] Redis integration for caching
- [ ] Basic JWT authentication

### Phase 2: API Completeness (Weeks 4-5)
- [ ] Complete REST API for all metrics
- [ ] Celery workers and Beat scheduler
- [ ] WebSocket endpoint for real-time updates
- [ ] Comprehensive error handling
- [ ] Request validation and sanitization

### Phase 3: Web Frontend (Weeks 6-8)
- [ ] React app scaffold with TypeScript
- [ ] Dashboard components
- [ ] Real-time chart updates via WebSocket
- [ ] Configuration management UI
- [ ] User authentication flow

### Phase 4: Alerting System (Weeks 9-10)
- [ ] Alert rule engine
- [ ] Multi-channel notifications (email, Slack, push)
- [ ] Alert management interface
- [ ] Suppression and escalation logic

### Phase 5: Mobile App (Weeks 11-13)
- [ ] Flutter project setup
- [ ] Core screens (dashboard, sessions, alerts)
- [ ] Offline capability with Hive
- [ ] Push notification integration
- [ ] App store release prep

### Phase 6: Testing & Documentation (Weeks 14-15)
- [ ] Unit and integration tests (>80% coverage)
- [ ] E2E tests
- [ ] Load testing and performance optimization
- [ ] API documentation and admin guides
- [ ] Security review and hardening

### Phase 7: Production Deployment (Week 16)
- [ ] Docker image building and registry setup
- [ ] Kubernetes manifests
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Monitoring and alerting for the monitor itself
- [ ] Runbooks and incident response guides

---

## 9. Security Considerations

### 9.1 Authentication & Authorization

- **JWT Tokens**: 15-minute expiry with refresh tokens (7-day validity)
- **MFA**: TOTP-based for privileged operations
- **RBAC Roles**: Admin, DBA, Analyst, Viewer
- **Session Management**: Redis-backed, IP pinning option

### 9.2 Data Protection

- **TLS in Transit**: All connections (Oracle, PostgreSQL, API, client)
- **Encryption at Rest**: PostgreSQL transparent data encryption (TDE)
- **Secret Management**: HashiCorp Vault for Oracle credentials
- **API Keys**: Not stored plaintext, hashed with bcrypt

### 9.3 Audit & Compliance

- **Audit Trail**: All user actions logged (who, what, when, from where)
- **Data Retention**: Comply with legal holds and regulatory requirements
- **GDPR**: User data export/deletion endpoints, consent tracking
- **SOC 2**: Logging, monitoring, and incident response procedures

### 9.4 Vulnerability Prevention

- **SQL Injection**: Parameterized queries, ORM use
- **XSS Prevention**: Input sanitization, CSP headers, React auto-escaping
- **CSRF Protection**: Token-based, SameSite cookies
- **Rate Limiting**: Per-user and per-IP limits
- **Dependency Scanning**: Dependabot for Python and npm packages

---

## 10. Known Challenges & Mitigation Strategies

### Challenge 1: Oracle Connection Overhead
**Problem**: Frequent Oracle queries can impact production database performance.

**Mitigation**:
- Implement intelligent caching (5-30s TTL based on metric freshness requirements)
- Use read-only connections
- Queries on standby database if available
- Monitor collection job duration; alert if >1 second

### Challenge 2: Real-time Sync Across Multiple Clients
**Problem**: Broadcasting metrics to 100+ concurrent users without lag.

**Mitigation**:
- WebSocket connections with server-side broadcast queues
- Client-side deduplication (ignore updates < 1 second apart)
- Delta updates (only send changed values)
- Optional: Message queue (RabbitMQ) for guaranteed delivery

### Challenge 3: Mobile Battery Drain
**Problem**: Constant background polling drains mobile device battery.

**Mitigation**:
- Adaptive polling intervals (increase when app backgrounded)
- Use platform-specific background fetch APIs
- Local caching with Hive for offline viewing
- User-configurable refresh rates

### Challenge 4: Credential Exposure in Logs
**Problem**: Oracle passwords or API keys accidentally logged.

**Mitigation**:
- Log sanitization filters (redact passwords, tokens)
- No logging of request/response bodies
- Separate secret management system (Vault)
- Automated secret scanning in CI/CD (TruffleHog)

### Challenge 5: Multi-instance Performance Degradation
**Problem**: Monitoring 50+ Oracle instances causes proportional latency increase.

**Mitigation**:
- Distributed collectors (one worker per 10 instances)
- Metric aggregation and sampling at scale
- Database replication for reads
- Consider VectorDB for trend analysis

---

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dashboard Load Time | <1s | Lighthouse/WebPageTest |
| API Response Time (p99) | <500ms | Prometheus histogram |
| Metric Collection Latency | <5s | Collector task duration |
| Alert Detection Time | <30s | Alert triggering latency |
| Uptime | 99.9% | Synthetic monitoring |
| False Alert Rate | <5% | Manual review |
| User Adoption | >80% of DBAs | Quarterly survey |

---

## Conclusion

This specification provides a comprehensive foundation for building a production-grade Oracle monitoring system. The phased approach balances feature delivery with quality, and the detailed component design ensures scalability and maintainability. Regular reviews and feedback from early users will guide refinement in subsequent phases.
