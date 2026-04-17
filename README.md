# Oracle Database Monitoring System

A production-grade, real-time database monitoring platform for Oracle instances, providing web and mobile dashboards, alerting, and historical analysis.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for web frontend)
- Flutter 3.x (for mobile development)

### Local Development

```bash
# Clone and setup
git clone <repo>
cd oracle_monitor

# Start services (API, PostgreSQL, Redis, Celery)
docker-compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start API server
uvicorn app.main:app --reload

# In another terminal, start Celery worker
celery -A collector.tasks worker -l info

# Start Celery Beat scheduler
celery -A collector.tasks beat -l info
```

### Frontend Setup

```bash
cd web/frontend
npm install
npm start  # Starts React dev server on http://localhost:3000
```

### Mobile Setup

```bash
cd mobile
flutter pub get
flutter run -d chrome  # Web emulator for testing
flutter run -d emulator-5554  # Android emulator
```

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Project overview, tech stack, architecture decisions
- **[TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md)** - Detailed design, API specs, schema
- **[API Documentation](./backend/docs/API.md)** - REST endpoint reference
- **[Database Schema](./backend/docs/SCHEMA.md)** - PostgreSQL and Oracle integration details

## Project Structure

```
oracle_monitor/
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── main.py            # FastAPI app initialization
│   │   ├── models/            # Pydantic models
│   │   ├── routers/           # API route handlers
│   │   ├── middleware/        # Auth, logging, error handling
│   │   └── schemas/           # Request/response schemas
│   ├── collector/
│   │   ├── tasks.py           # Celery tasks
│   │   ├── oracle_client.py   # Oracle integration
│   │   └── metrics/           # Metric collection modules
│   ├── alerts/
│   │   ├── engine.py          # Alert rule evaluation
│   │   ├── notifier.py        # Notification channels
│   │   └── rules.py           # Rule definitions
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── migrations/        # Alembic migrations
│   ├── tests/                 # Unit and integration tests
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── web/                        # Django + React
│   ├── frontend/              # React SPA
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   ├── hooks/
│   │   │   └── App.tsx
│   │   ├── package.json
│   │   └── Dockerfile
│   └── django/
│       ├── manage.py
│       ├── settings.py
│       └── urls.py
├── mobile/                    # Flutter app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── widgets/
│   │   ├── services/
│   │   └── models/
│   ├── pubspec.yaml
│   └── Dockerfile
├── k8s/                       # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── docker-compose.yml
├── CLAUDE.md
├── TECHNICAL_SPECIFICATION.md
└── README.md
```

## Features

### Core Monitoring
- ✅ Real-time active sessions tracking
- ✅ Lock and blocking session detection
- ✅ Tablespace usage and capacity monitoring
- ✅ Slow query identification and analysis
- ✅ CPU and memory utilization tracking
- ✅ System alerts and notifications

### User Interface
- ✅ Web dashboard (React + TypeScript)
- ✅ Mobile app (Flutter, iOS/Android)
- ✅ Real-time metric updates (WebSocket)
- ✅ Configuration management UI
- ✅ Drill-down analysis views

### System
- ✅ Multi-instance support
- ✅ Role-based access control (RBAC)
- ✅ Configurable alerting with multiple channels
- ✅ Historical data analysis (90+ days)
- ✅ Comprehensive audit logging

## Testing

```bash
# Backend unit tests
cd backend
pytest tests/unit -v

# Integration tests (requires Docker)
pytest tests/integration -v

# Frontend tests
cd web/frontend
npm test

# E2E tests
npm run test:e2e

# Mobile tests
cd mobile
flutter test
```

## Deployment

### Docker Compose (Development/Staging)
```bash
docker-compose up -d
```

### Kubernetes (Production)
```bash
kubectl apply -f k8s/
kubectl port-forward svc/oracle-monitor-api 8000:8000
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and update:

```bash
# Oracle connections
ORACLE_INSTANCES='[{"name":"prod","user":"monitor","password":"xxx","dsn":"prod.local:1521/PROD"}]'

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/oracle_monitor
REDIS_URL=redis://localhost:6379

# Auth
SECRET_KEY=your-secret-key
JWT_EXPIRY=900  # 15 minutes

# Notifications
SMTP_HOST=mail.example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## API Endpoints

### Metrics
- `GET /api/metrics/overview` - Summary metrics
- `GET /api/metrics/{type}` - Specific metric history
- `GET /api/sessions` - Active sessions
- `GET /api/locks` - Lock information
- `GET /api/slow-queries` - Slow queries

### Alerts
- `GET /api/alerts` - Alert history
- `POST /api/alerts/rules` - Create rule
- `PUT /api/alerts/rules/{id}` - Update rule
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert

### Configuration
- `POST /api/instances` - Add database instance
- `PUT /api/instances/{id}` - Update instance
- `GET /api/users` - Manage users (admin only)

See [API Documentation](./backend/docs/API.md) for complete reference.

## Performance Targets

| Component | Target |
|-----------|--------|
| Dashboard Load | <1s |
| API Response (p99) | <500ms |
| Metric Collection | <5s |
| Alert Detection | <30s |
| System Uptime | 99.9% |

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Submit PR for review
4. Deploy to staging for validation

## Support

- **Documentation**: See [TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md)
- **Issues**: GitHub Issues
- **Team**: #oracle-monitoring Slack channel

## License

Proprietary - Internal Use Only
