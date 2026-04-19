# Oracle Monitor - Security Guidelines

## Authentication & Authorization

### JWT Token Security

1. **Token Generation**:
   - Use strong secret keys (minimum 32 characters)
   - Token expiry: 15 minutes for access tokens
   - Refresh tokens: 7 days with rotation

2. **Token Storage** (Frontend):
   - Store access tokens in memory only
   - Store refresh tokens in secure, httpOnly cookies
   - Never store tokens in localStorage

3. **Token Validation**:
   - Always validate token signature
   - Check token expiry
   - Verify user is still active

### Role-Based Access Control (RBAC)

```
Roles:
- Admin: Full system access
- DBA: Database metrics and alerts
- Analyst: Read-only access to metrics and reports
- Viewer: Limited read access to dashboards
```

**Implementation**:
```python
# Always check permissions in endpoints
@router.get("/admin/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    if "admin" not in current_user.role.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # ...
```

---

## Data Security

### Encryption

1. **In Transit**:
   - TLS 1.2+ for all connections
   - HSTS header enabled
   - HTTPS enforcement

2. **At Rest**:
   - Database encryption (PostgreSQL pgcrypto)
   - Sensitive fields encrypted at application level
   - Encrypted backups

3. **Secrets Management**:
   - Use Kubernetes Secrets or HashiCorp Vault
   - Never commit secrets to git
   - Rotate secrets regularly

### Data Classification

| Data | Classification | Handling |
|------|-----------------|----------|
| User credentials | Highly Sensitive | Hashed (bcrypt) |
| API tokens | Sensitive | Encrypted, short-lived |
| Database metrics | Internal Use | Access controlled |
| Logs | Sensitive | Encrypted, retention policy |
| Backups | Sensitive | Encrypted, access controlled |

---

## Network Security

### Network Policies

Apply strict network policies:

```yaml
# Only allow frontend->API traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      component: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          component: frontend
    ports:
    - protocol: TCP
      port: 8000
```

### API Security

1. **Rate Limiting**:
   ```
   - 100 requests per minute per user
   - 1000 requests per minute per IP
   - Circuit breaker for failing endpoints
   ```

2. **Input Validation**:
   ```python
   # Always validate and sanitize inputs
   class MetricQuery(BaseModel):
       instance_id: int = Field(..., gt=0)
       metric_type: str = Field(..., min_length=1, max_length=50)
       start_date: datetime = Field(default_factory=datetime.utcnow)
   ```

3. **SQL Injection Prevention**:
   - Use parameterized queries (SQLAlchemy ORM)
   - Never construct SQL strings with user input
   - Validate all input data types

4. **CORS Configuration**:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[os.getenv("ALLOWED_ORIGINS", "https://app.example.com")],
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["Content-Type", "Authorization"],
   )
   ```

---

## Application Security

### Dependency Management

```bash
# Regular dependency audits
pip install -r backend/requirements.txt --upgrade
npm audit --audit-level=moderate

# Track CVE vulnerabilities
safety check
npm audit
```

### Logging & Monitoring

1. **Sensitive Data in Logs**:
   ```python
   # ✓ Good: No sensitive data
   logger.info(f"User {user_id} logged in")
   
   # ✗ Bad: Exposes password
   logger.info(f"User login with password: {password}")
   ```

2. **Log Retention**:
   - Application logs: 30 days
   - Audit logs: 1 year
   - Error logs: 90 days

3. **Monitoring Alerts**:
   - Failed authentication attempts (>5 per minute)
   - Unauthorized access attempts
   - Data access violations
   - Configuration changes

### Code Security

1. **Code Review**:
   - All code requires peer review
   - Security-focused review checklist
   - Automated SAST scanning

2. **Static Analysis**:
   ```bash
   # Python security scanning
   bandit -r backend/
   
   # JavaScript dependency check
   npm audit
   npm install --save-dev eslint-plugin-security
   ```

3. **Secrets Detection**:
   ```bash
   # Scan for exposed secrets
   git secrets --scan
   detect-secrets scan
   ```

---

## Infrastructure Security

### Container Security

1. **Image Security**:
   ```dockerfile
   # ✓ Good: Use specific versions
   FROM python:3.11-slim
   RUN useradd -m -u 1000 appuser
   USER appuser
   
   # ✗ Bad: Latest tag, root user
   FROM python:latest
   ```

2. **Scanning**:
   ```bash
   # Scan images for vulnerabilities
   docker scan oracle-monitor-backend:latest
   trivy image oracle-monitor-backend:latest
   ```

### Kubernetes Security

1. **Pod Security Standards**:
   ```yaml
   # Apply pod security policies
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     allowPrivilegeEscalation: false
     readOnlyRootFilesystem: true
     capabilities:
       drop: ["ALL"]
   ```

2. **RBAC Configuration**:
   ```bash
   # Least privilege access
   kubectl create serviceaccount oracle-monitor-api
   kubectl create role api-role --verb=get --resource=configmaps
   kubectl create rolebinding api-binding --role=api-role --serviceaccount=oracle-monitor:oracle-monitor-api
   ```

3. **Network Policies**:
   - Deny all ingress/egress by default
   - Allow only necessary traffic
   - Isolate workloads by namespace

---

## Secure Deployment Checklist

- [ ] All secrets in Kubernetes Secrets (not ConfigMaps)
- [ ] TLS certificates configured and valid
- [ ] HTTPS enforced (HSTS header)
- [ ] Network policies applied
- [ ] Pod security context configured
- [ ] Resource limits set
- [ ] Health checks configured
- [ ] Logging enabled and monitored
- [ ] Backup strategy tested
- [ ] Disaster recovery plan documented
- [ ] Security scanning in CI/CD
- [ ] Dependency vulnerabilities scanned
- [ ] API rate limiting enabled
- [ ] Authentication/authorization tested
- [ ] Audit logging enabled

---

## Incident Response

### Security Incident Classification

| Level | Example | Response Time |
|-------|---------|----------------|
| Critical | Data breach, unauthorized access | 1 hour |
| High | Suspected intrusion, unpatched vulnerability | 4 hours |
| Medium | Suspicious activity, policy violation | 24 hours |
| Low | Security warning, audit finding | 1 week |

### Incident Response Steps

1. **Detect**: Monitor logs and alerts
2. **Contain**: Isolate affected systems
3. **Investigate**: Determine scope and cause
4. **Eradicate**: Remove the threat
5. **Recover**: Restore normal operations
6. **Review**: Post-incident analysis

---

## Compliance

### Data Protection

- GDPR: User data rights and retention policies
- CCPA: Privacy notices and opt-out mechanisms
- HIPAA: If handling healthcare data

### Auditing

```python
# Audit all sensitive operations
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    action = Column(String(50))
    resource = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON)
```

---

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html#SQL-SYNTAX-LEXICAL)

## Reporting Security Issues

If you discover a security vulnerability:
1. Do NOT create a public issue
2. Email security@example.com with details
3. Include reproduction steps if possible
4. Allow 30 days for remediation before disclosure

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-04-19 | 1.0 | Initial security guidelines |

For questions or updates, contact the Security Team.
