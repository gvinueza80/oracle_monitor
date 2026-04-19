# Oracle Monitor - Deployment Guide

## Prerequisites

- Kubernetes 1.24+ cluster
- kubectl configured with appropriate context
- Helm 3.x (optional, for package management)
- Docker registry access for pulling images

## Local Development Deployment

### Using Docker Compose

```bash
# Build all services
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec api python -m alembic upgrade head

# Stop services
docker-compose down
```

### Accessing the Application

- Web UI: http://localhost:3000
- API: http://localhost:8000/api
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3001 (admin/admin)

## Kubernetes Deployment

### 1. Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace oracle-monitor

# Create secrets (update values before applying)
kubectl create secret generic oracle-monitor-secrets \
  --from-literal=database-url='postgresql+asyncpg://postgres:PASSWORD@oracle-monitor-postgres:5432/oracle_monitor' \
  --from-literal=postgres-password='SECURE_PASSWORD' \
  --from-literal=jwt-secret='JWT_SECRET_KEY' \
  -n oracle-monitor
```

### 2. Deploy Database Services

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres-statefulset.yaml

# Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml

# Wait for services to be ready
kubectl wait --for=condition=ready pod -l component=postgres -n oracle-monitor --timeout=300s
kubectl wait --for=condition=ready pod -l component=redis -n oracle-monitor --timeout=300s
```

### 3. Run Database Migrations

```bash
# Create migration job
kubectl run -it --rm oracle-monitor-migrate \
  --image=oracle-monitor-backend:latest \
  --restart=Never \
  -n oracle-monitor \
  -- python -m alembic upgrade head
```

### 4. Deploy Application Services

```bash
# Deploy API
kubectl apply -f k8s/api-deployment.yaml

# Deploy Frontend
kubectl apply -f k8s/frontend-deployment.yaml

# Deploy Ingress
kubectl apply -f k8s/ingress.yaml

# Wait for deployments
kubectl wait --for=condition=available --timeout=300s deployment \
  -l component=api -n oracle-monitor
kubectl wait --for=condition=available --timeout=300s deployment \
  -l component=frontend -n oracle-monitor
```

### 5. Verify Deployment

```bash
# Check all resources
kubectl get all -n oracle-monitor

# Check ingress
kubectl get ingress -n oracle-monitor

# Check pod logs
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor

# Port forward for testing
kubectl port-forward svc/oracle-monitor-api 8000:80 -n oracle-monitor
```

## Configuration Management

### Environment Variables

Key environment variables for the API:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
REDIS_URL=redis://host:6379/0
JWT_SECRET=your-secret-key
ORACLE_CONNECTION_POOL_SIZE=10
LOG_LEVEL=INFO
```

### ConfigMaps and Secrets

Update the ConfigMap for non-sensitive configuration:

```bash
kubectl edit configmap oracle-monitor-config -n oracle-monitor
```

Update secrets for sensitive data:

```bash
kubectl create secret generic oracle-monitor-secrets \
  --from-literal=database-url='...' \
  --from-literal=jwt-secret='...' \
  -n oracle-monitor \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Scaling and High Availability

### Scale API Deployment

```bash
# Manual scaling
kubectl scale deployment oracle-monitor-api --replicas=5 -n oracle-monitor

# View HPA status
kubectl get hpa -n oracle-monitor
```

### Database Backup

```bash
# Create on-demand backup
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  pg_dump -U postgres oracle_monitor > backup-$(date +%Y%m%d).sql

# Restore from backup
kubectl exec -i oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres oracle_monitor < backup-20240419.sql
```

## Monitoring and Logging

### View Metrics

```bash
# Port forward to Prometheus (if deployed)
kubectl port-forward svc/prometheus 9090:9090 -n monitoring

# Port forward to Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring
```

### View Application Logs

```bash
# Stream API logs
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor

# Stream frontend logs
kubectl logs -f deployment/oracle-monitor-frontend -n oracle-monitor

# View logs with labels
kubectl logs -f -l component=api -n oracle-monitor
```

### View Events

```bash
# Watch cluster events
kubectl get events -n oracle-monitor --sort-by='.lastTimestamp'
```

## Troubleshooting

### Pod Fails to Start

```bash
# Check pod status
kubectl describe pod <pod-name> -n oracle-monitor

# View pod events
kubectl get events -n oracle-monitor

# Check resource constraints
kubectl top nodes
kubectl top pods -n oracle-monitor
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it oracle-monitor-api-0 -n oracle-monitor -- \
  python -c "from db import engine; import asyncio; asyncio.run(engine.begin())"

# Check DNS resolution
kubectl exec -it oracle-monitor-api-0 -n oracle-monitor -- \
  nslookup oracle-monitor-postgres
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n oracle-monitor

# View resource limits
kubectl describe nodes

# Check HPA status
kubectl describe hpa oracle-monitor-api-hpa -n oracle-monitor
```

## Upgrades and Updates

### Rolling Update

```bash
# Update image
kubectl set image deployment/oracle-monitor-api \
  api=new-image:tag -n oracle-monitor

# Monitor rollout
kubectl rollout status deployment/oracle-monitor-api -n oracle-monitor

# Rollback if needed
kubectl rollout undo deployment/oracle-monitor-api -n oracle-monitor
```

### Database Migration During Upgrade

```bash
# Create pre-upgrade snapshot
kubectl exec oracle-monitor-postgres-0 -n oracle-monitor -- \
  pg_dump -U postgres oracle_monitor > pre-upgrade-backup.sql

# Apply migrations
kubectl run -it --rm migrate \
  --image=oracle-monitor-backend:new-tag \
  --restart=Never \
  -n oracle-monitor \
  -- python -m alembic upgrade head

# Monitor rollout
kubectl rollout status deployment/oracle-monitor-api -n oracle-monitor
```

## Security Best Practices

1. **RBAC**: Ensure proper RBAC policies are in place
2. **Network Policies**: Apply network policies to restrict traffic
3. **Secrets Management**: Use a secrets management solution (Vault, Sealed Secrets)
4. **Image Scanning**: Scan container images for vulnerabilities
5. **Pod Security**: Use Pod Security Policies or Pod Security Standards
6. **TLS**: Enable TLS for all ingress traffic

## Cost Optimization

1. **Resource Limits**: Set appropriate resource requests and limits
2. **HPA**: Use Horizontal Pod Autoscaler for cost efficiency
3. **Node Affinity**: Distribute workloads across nodes
4. **Storage**: Use appropriate storage classes and retention policies

## Support and Debugging

For detailed debugging:

```bash
# Get detailed cluster information
kubectl cluster-info dump --output-directory=./cluster-dump

# Enable verbose logging
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor --all-containers=true --tail=100
```

## Next Steps

1. Configure monitoring and alerting
2. Set up CI/CD pipeline for automated deployments
3. Configure backup and disaster recovery
4. Implement security policies
5. Set up logging aggregation (ELK, Datadog, etc.)
