# Oracle Monitor - Operational Runbooks

## Emergency Procedures

### 1. Service Outage Response

**Incident**: Complete service unavailability (all endpoints returning errors)

**Detection**:
- Monitoring alerts trigger for multiple health checks
- Users report inability to access dashboard
- API errors in error tracking system

**Response Steps**:

```bash
# 1. Check cluster health
kubectl get nodes -o wide
kubectl get pods -n oracle-monitor

# 2. Check deployment status
kubectl get deployments -n oracle-monitor

# 3. View recent events
kubectl get events -n oracle-monitor --sort-by='.lastTimestamp' | head -20

# 4. Check API logs for errors
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor --tail=100

# 5. Check database connectivity
kubectl exec -it oracle-monitor-api-0 -n oracle-monitor -- \
  python -c "from db import engine; import asyncio; print(asyncio.run(engine.begin()))"

# 6. If database issue, check postgres
kubectl logs -f statefulset/oracle-monitor-postgres -n oracle-monitor

# 7. Check Redis
kubectl logs -f deployment/oracle-monitor-redis -n oracle-monitor

# 8. If needed, restart API pods
kubectl rollout restart deployment/oracle-monitor-api -n oracle-monitor

# 9. Monitor recovery
kubectl get pods -n oracle-monitor -w
```

**Escalation**:
- If issue persists >5 minutes: Page on-call engineer
- If database is down: Initiate database recovery procedure

---

### 2. Database Recovery

**Incident**: PostgreSQL pod crashed or database is corrupted

**Recovery Steps**:

```bash
# 1. Check database pod status
kubectl describe pod oracle-monitor-postgres-0 -n oracle-monitor

# 2. Check PVC status
kubectl get pvc -n oracle-monitor

# 3. View database logs
kubectl logs oracle-monitor-postgres-0 -n oracle-monitor

# 4. Attempt pod restart
kubectl delete pod oracle-monitor-postgres-0 -n oracle-monitor

# 5. Wait for pod to recover
kubectl wait --for=condition=ready pod/oracle-monitor-postgres-0 \
  -n oracle-monitor --timeout=300s

# 6. Verify data integrity
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor -c "SELECT count(*) FROM metrics;"

# 7. If corrupted, restore from backup
# (See backup recovery section below)
```

**Backup Recovery**:

```bash
# 1. Create new database
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  createdb -U postgres oracle_monitor_recovery

# 2. Restore from backup
kubectl exec -i oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres oracle_monitor_recovery < /backups/latest.sql

# 3. Verify restored data
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor_recovery -c "SELECT count(*) FROM metrics;"

# 4. Swap databases
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -c "DROP DATABASE oracle_monitor; \
    ALTER DATABASE oracle_monitor_recovery RENAME TO oracle_monitor;"

# 5. Restart API pods to reconnect
kubectl rollout restart deployment/oracle-monitor-api -n oracle-monitor
```

---

### 3. High Memory Usage

**Incident**: API pods consuming excessive memory, potential OOM kills

**Detection**:
- `kubectl top pods -n oracle-monitor` shows high memory usage
- OOMKilled events in pod status

**Diagnosis**:

```bash
# 1. Check pod memory usage
kubectl top pods -n oracle-monitor

# 2. Check memory limits
kubectl describe pod oracle-monitor-api-0 -n oracle-monitor | grep -A 5 "Limits"

# 3. Check for memory leaks in logs
kubectl logs deployment/oracle-monitor-api -n oracle-monitor | \
  grep -i "memory\|gc\|heap"

# 4. Check Redis memory
kubectl exec -it oracle-monitor-redis-0 -n oracle-monitor -- \
  redis-cli info memory
```

**Remediation**:

```bash
# 1. Increase memory limits
kubectl set resources deployment oracle-monitor-api \
  --limits=memory=2Gi --requests=memory=1Gi \
  -n oracle-monitor

# 2. Restart pods with new limits
kubectl rollout restart deployment/oracle-monitor-api -n oracle-monitor

# 3. If issue persists, clear Redis cache
kubectl exec -it oracle-monitor-redis-0 -n oracle-monitor -- \
  redis-cli FLUSHDB

# 4. If still issues, scale down temporarily
kubectl scale deployment oracle-monitor-api --replicas=1 \
  -n oracle-monitor
```

---

### 4. Database Connection Pool Exhaustion

**Incident**: "Connection pool exhausted" errors in logs

**Detection**:
- API returning 503 Service Unavailable
- Logs showing connection pool errors
- Active connections at max pool size

**Response**:

```bash
# 1. Check active connections
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Check long-running queries
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -c "SELECT pid, query, query_start FROM pg_stat_activity \
    WHERE query NOT LIKE '%pg_stat_activity%' ORDER BY query_start;"

# 3. Kill idle connections
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
    WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"

# 4. Increase connection pool size
kubectl set env deployment/oracle-monitor-api \
  DATABASE_POOL_SIZE=20 \
  -n oracle-monitor

# 5. Restart API
kubectl rollout restart deployment/oracle-monitor-api -n oracle-monitor
```

---

### 5. High API Latency

**Incident**: API responses slow, users experiencing timeouts

**Investigation**:

```bash
# 1. Check API response times
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor | \
  grep "duration\|latency"

# 2. Check database query performance
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor -c "\
    SELECT query, calls, mean_exec_time FROM pg_stat_statements \
    ORDER BY mean_exec_time DESC LIMIT 10;"

# 3. Check for slow queries in Slow Query Log
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  tail -f /var/log/postgresql/postgresql.log | grep "duration"

# 4. Check Redis latency
kubectl exec -it oracle-monitor-redis-0 -n oracle-monitor -- \
  redis-cli --latency

# 5. Check CPU usage
kubectl top nodes
kubectl top pods -n oracle-monitor
```

**Optimization**:

```bash
# 1. Analyze slow queries
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor -c "EXPLAIN ANALYZE <slow-query>;"

# 2. Add database indexes if needed
# (Update db/models.py and run migrations)

# 3. Clear Redis cache if needed
kubectl exec -it oracle-monitor-redis-0 -n oracle-monitor -- \
  redis-cli FLUSHDB

# 4. Scale up API replicas
kubectl scale deployment oracle-monitor-api --replicas=5 \
  -n oracle-monitor

# 5. Monitor improvement
kubectl logs -f deployment/oracle-monitor-api -n oracle-monitor
```

---

### 6. Certificate Expiration

**Incident**: HTTPS certificate expired or expiring soon

**Detection**:
- Browser SSL warnings
- Cert-manager alerts

**Renewal**:

```bash
# 1. Check certificate status
kubectl get certificate -n oracle-monitor

# 2. View cert details
kubectl describe certificate oracle-monitor-tls -n oracle-monitor

# 3. Force cert renewal
kubectl delete secret oracle-monitor-tls -n oracle-monitor

# 4. Force cert-manager to issue new cert
kubectl delete certificate oracle-monitor-tls -n oracle-monitor
kubectl apply -f k8s/ingress.yaml

# 5. Verify new certificate
kubectl get certificate -n oracle-monitor -w
```

---

## Maintenance Procedures

### Daily Tasks

```bash
# Check overall health
kubectl get nodes
kubectl get pods -n oracle-monitor
kubectl get pvc -n oracle-monitor

# Review recent events
kubectl get events -n oracle-monitor --sort-by='.lastTimestamp'

# Check available disk space
kubectl top nodes
df -h /var/lib/kubelet/pods
```

### Weekly Tasks

```bash
# Check database size
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor -c "SELECT pg_database.datname, \
    pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database \
    WHERE datname = 'oracle_monitor';"

# Analyze slow queries
kubectl exec -it oracle-monitor-postgres-0 -n oracle-monitor -- \
  psql -U postgres -d oracle_monitor -c "REINDEX DATABASE oracle_monitor;"

# Review error logs
kubectl logs deployment/oracle-monitor-api -n oracle-monitor --tail=1000 | \
  grep ERROR
```

### Monthly Tasks

```bash
# Create backup
kubectl exec oracle-monitor-postgres-0 -n oracle-monitor -- \
  pg_dump -U postgres oracle_monitor > \
  oracle_monitor_backup_$(date +%Y%m%d).sql

# Test backup restoration
docker run --rm -v $(pwd):/backup postgres:15 \
  psql -c "CREATE DATABASE test_restore; \
    psql -d test_restore < /backup/oracle_monitor_backup_*.sql"

# Review and update security policies
kubectl get networkpolicies -n oracle-monitor

# Update dependencies and container images
docker pull oracle-monitor-backend:latest
docker pull oracle-monitor-frontend:latest
```

---

## Escalation Matrix

| Severity | Issue | Initial Response | Escalation |
|----------|-------|------------------|------------|
| Critical | Complete outage | Immediate investigation | Page on-call within 5 min |
| High | Partial service failure | Investigate within 15 min | Manager notified |
| Medium | Performance degradation | Investigate within 1 hour | Team meeting scheduled |
| Low | Minor issues/warnings | Monitor and resolve | Regular review |

---

## Contact Information

- **On-Call Engineer**: Check PagerDuty
- **Database Admin**: db-team@company.com
- **Infrastructure**: infra-team@company.com
- **Security**: security-team@company.com

## References

- [Kubernetes Docs](https://kubernetes.io/docs/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Redis Docs](https://redis.io/documentation)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
