# ViolentUTF API Deployment & Operations Guide

Comprehensive documentation for deploying, configuring, and operating the ViolentUTF API platform in various environments, from development to production.

## 🏗️ Deployment Architecture

ViolentUTF consists of multiple containerized services working together:

```
┌─────────────────────────────────────────────────────────────────┐
│                Production Deployment                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Load Balancer │   Application   │        Data Layer           │
│    (Optional)   │     Services    │                             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • NGINX/HAProxy │ • APISIX Gateway│ • PostgreSQL (Keycloak)    │
│ • SSL/TLS Term  │ • FastAPI App   │ • DuckDB (PyRIT Memory)     │
│ • Rate Limiting │ • Keycloak SSO  │ • File Storage              │
│ • Monitoring    │ • Streamlit UI  │ • Log Storage               │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## 🚀 Quick Deployment

### Prerequisites

**System Requirements:**
- Docker 20.10+ and Docker Compose 2.0+
- Python 3.9+ (for setup scripts)
- 8GB RAM minimum, 16GB recommended
- 20GB disk space for containers and data

**Network Requirements:**
- Ports 8080, 8501, 9080, 9180, 9001 available
- External internet access for AI provider APIs
- DNS resolution for container networking

### Automated Setup (Recommended)

**macOS/Linux:**
```bash
# Clone repository
git clone <repository-url> violentutf
cd violentutf

# Run automated setup
./setup_macos.sh

# Verify deployment
cd apisix && ./verify_routes.sh
```

**Windows:**
```cmd
# Clone repository
git clone <repository-url> violentutf
cd violentutf

# Run Windows setup
setup_windows.bat

# Verify deployment
cd apisix
verify_routes.bat
```

### Manual Setup

For custom configurations or troubleshooting:

#### 1. Environment Preparation
```bash
# Create Python virtual environment
python3 -m venv .vitutf
source .vitutf/bin/activate  # Linux/macOS
# or .vitutf\Scripts\activate  # Windows

# Install Python dependencies
pip install -r violentutf/requirements.txt
```

#### 2. Generate Configuration
```bash
# Generate secure secrets
JWT_SECRET=$(openssl rand -base64 32)
APISIX_ADMIN_KEY=$(openssl rand -base64 32)
APISIX_GATEWAY_SECRET=$(openssl rand -hex 32)

# Create environment files
cat > violentutf/.env << EOF
JWT_SECRET_KEY=$JWT_SECRET
VIOLENTUTF_API_KEY=$APISIX_ADMIN_KEY
VIOLENTUTF_API_URL=http://localhost:9080
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=ViolentUTF
EOF

cat > violentutf_api/fastapi_app/.env << EOF
SECRET_KEY=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY
APISIX_GATEWAY_SECRET=$APISIX_GATEWAY_SECRET
EOF
```

#### 3. Start Services
```bash
# Start Keycloak
cd keycloak && docker compose up -d

# Start APISIX Gateway
cd ../apisix && docker compose up -d

# Configure routes
./configure_routes.sh

# Start FastAPI
cd ../violentutf_api && docker compose up -d

# Start Streamlit
cd ../violentutf
streamlit run Home.py --server.port 8501 --server.address 0.0.0.0
```

## 🏢 Production Deployment

### Production Architecture

```
                    Internet
                       │
                       ▼
              ┌─────────────────┐
              │  Load Balancer  │
              │   (NGINX/AWS)   │
              └─────────────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
    ┌───────────┐ ┌──────────┐ ┌──────────┐
    │  APISIX   │ │ APISIX   │ │ APISIX   │
    │ Gateway 1 │ │Gateway 2 │ │Gateway 3 │
    └───────────┘ └──────────┘ └──────────┘
           │           │           │
           └───────────┼───────────┘
                       ▼
              ┌─────────────────┐
              │   FastAPI       │
              │   Services      │
              │  (Replicated)   │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Data Layer    │
              │ PostgreSQL/etc  │
              └─────────────────┘
```

### Production Environment Setup

#### 1. SSL/TLS Configuration

**NGINX Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.violentutf.com;

    ssl_certificate /etc/ssl/certs/violentutf.crt;
    ssl_certificate_key /etc/ssl/private/violentutf.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    location / {
        proxy_pass http://apisix_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

upstream apisix_backend {
    least_conn;
    server apisix1:9080 max_fails=3 fail_timeout=30s;
    server apisix2:9080 max_fails=3 fail_timeout=30s;
    server apisix3:9080 max_fails=3 fail_timeout=30s;
}
```

#### 2. Database Configuration

**PostgreSQL for Keycloak:**
```yaml
# docker-compose.prod.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 4G
          cpus: '2'
```

**Production PostgreSQL Configuration:**
```conf
# postgresql.conf
max_connections = 200
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### 3. Environment Variables

**Production Environment Template:**
```bash
# Core Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=${PRODUCTION_SECRET_KEY}
JWT_SECRET_KEY=${PRODUCTION_JWT_SECRET}

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/violentutf
REDIS_URL=redis://redis:6379/0

# Authentication
KEYCLOAK_URL=https://auth.violentutf.com
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_PROD_SECRET}

# API Gateway
APISIX_BASE_URL=https://api.violentutf.com
APISIX_ADMIN_KEY=${APISIX_PROD_ADMIN_KEY}
APISIX_GATEWAY_SECRET=${APISIX_PROD_GATEWAY_SECRET}

# External Services
OPENAI_API_KEY=${OPENAI_PROD_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_PROD_KEY}

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PROD_PASSWORD}
LOG_LEVEL=INFO
```

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

networks:
  vutf-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  apisix:
    image: apache/apisix:3.2.0-debian
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '1'
    environment:
      - APISIX_STAND_ALONE=true
    volumes:
      - ./conf/apisix.yaml:/usr/local/apisix/conf/apisix.yaml:ro
      - ./conf/config.yaml:/usr/local/apisix/conf/config.yaml:ro
    networks:
      - vutf-network
    depends_on:
      - etcd
      - fastapi

  fastapi:
    build:
      context: ./violentutf_api/fastapi_app
      dockerfile: Dockerfile.prod
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '1'
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - app_data:/app/data
      - app_logs:/app/logs
    networks:
      - vutf-network
    depends_on:
      - postgres

  keycloak:
    image: quay.io/keycloak/keycloak:22.0
    command: start --optimized
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
      KC_HOSTNAME: auth.violentutf.com
      KC_PROXY: edge
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
          cpus: '1'
    networks:
      - vutf-network
    depends_on:
      - postgres

volumes:
  postgres_data:
    driver: local
  app_data:
    driver: local
  app_logs:
    driver: local
```

## 🔧 Configuration Management

### Environment-Specific Configuration

#### Development Configuration
```yaml
# config/development.yaml
environment: development
debug: true
log_level: DEBUG
cors:
  allowed_origins: ["http://localhost:8501", "http://localhost:3000"]
database:
  type: duckdb
  path: ./data/dev_violentutf.db
rate_limiting:
  enabled: false
```

#### Staging Configuration
```yaml
# config/staging.yaml
environment: staging
debug: false
log_level: INFO
cors:
  allowed_origins: ["https://staging.violentutf.com"]
database:
  type: postgresql
  url: postgresql://user:pass@staging-db:5432/violentutf
rate_limiting:
  enabled: true
  requests_per_second: 50
```

#### Production Configuration
```yaml
# config/production.yaml
environment: production
debug: false
log_level: WARNING
cors:
  allowed_origins: ["https://app.violentutf.com"]
database:
  type: postgresql
  url: postgresql://user:pass@prod-db:5432/violentutf
rate_limiting:
  enabled: true
  requests_per_second: 100
security:
  require_https: true
  hsts_max_age: 31536000
```

### Secret Management

#### Docker Secrets (Production)
```yaml
# docker-compose.secrets.yml
secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  postgres_password:
    file: ./secrets/postgres_password.txt
  keycloak_admin_password:
    file: ./secrets/keycloak_admin_password.txt

services:
  fastapi:
    secrets:
      - jwt_secret
      - postgres_password
    environment:
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
```

#### Kubernetes Secrets
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: violentutf-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  postgres-password: <base64-encoded-password>
  keycloak-admin-password: <base64-encoded-password>
```

## 🚀 Container Orchestration

### Docker Swarm Deployment

#### 1. Initialize Swarm
```bash
# On manager node
docker swarm init --advertise-addr <manager-ip>

# Join worker nodes
docker swarm join --token <worker-token> <manager-ip>:2377
```

#### 2. Deploy Stack
```bash
# Deploy ViolentUTF stack
docker stack deploy -c docker-compose.prod.yml violentutf

# Check service status
docker service ls
docker service logs violentutf_fastapi
```

### Kubernetes Deployment

#### 1. Namespace and ConfigMap
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: violentutf

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: violentutf-config
  namespace: violentutf
data:
  environment: "production"
  log_level: "INFO"
  keycloak_url: "https://auth.violentutf.com"
```

#### 2. Deployment Manifests
```yaml
# k8s/fastapi-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: violentutf-fastapi
  namespace: violentutf
spec:
  replicas: 3
  selector:
    matchLabels:
      app: violentutf-fastapi
  template:
    metadata:
      labels:
        app: violentutf-fastapi
    spec:
      containers:
      - name: fastapi
        image: violentutf/fastapi:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: violentutf-config
              key: environment
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: violentutf-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 3. Services and Ingress
```yaml
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: violentutf-fastapi-service
  namespace: violentutf
spec:
  selector:
    app: violentutf-fastapi
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: violentutf-ingress
  namespace: violentutf
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.violentutf.com
    secretName: violentutf-tls
  rules:
  - host: api.violentutf.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: apisix-service
            port:
              number: 9080
```

## 📊 Monitoring & Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9091']
    metrics_path: '/apisix/prometheus/metrics'

  - job_name: 'fastapi'
    static_configs:
      - targets: ['fastapi:8000']
    metrics_path: '/metrics'

  - job_name: 'keycloak'
    static_configs:
      - targets: ['keycloak:8080']
    metrics_path: '/auth/realms/ViolentUTF/metrics'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "ViolentUTF API Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(apisix_http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(apisix_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(apisix_http_requests_total{status=~\"5..\"}[5m]) / rate(apisix_http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

```yaml
# monitoring/alert_rules.yml
groups:
  - name: violentutf_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(apisix_http_requests_total{status=~"5.."}[5m]) / rate(apisix_http_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(apisix_http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: ServiceDown
        expr: up{job=~"fastapi|apisix|keycloak"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} service is not responding"
```

### Application Metrics

```python
# FastAPI metrics instrumentation
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    'fastapi_requests_total',
    'Total FastAPI requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'fastapi_request_duration_seconds',
    'FastAPI request duration',
    ['method', 'endpoint']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🔒 Security Hardening

### Container Security

#### 1. Multi-stage Dockerfile
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim as builder

# Install dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as runtime

# Create non-root user
RUN groupadd -r violentutf && useradd -r -g violentutf violentutf

# Copy dependencies from builder
COPY --from=builder /root/.local /home/violentutf/.local

# Copy application
WORKDIR /app
COPY --chown=violentutf:violentutf . .

# Switch to non-root user
USER violentutf

# Set PATH
ENV PATH=/home/violentutf/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Security Scanning
```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/tmp/.cache/ \
  aquasec/trivy image violentutf/fastapi:latest

# Scan for secrets
docker run --rm -v $(pwd):/path \
  trufflesecurity/trufflehog:latest filesystem /path
```

### Network Security

#### 1. Network Policies (Kubernetes)
```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: violentutf-network-policy
  namespace: violentutf
spec:
  podSelector:
    matchLabels:
      app: violentutf-fastapi
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: apisix
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to: []
      ports:
        - protocol: TCP
          port: 443  # HTTPS only for external APIs
```

#### 2. TLS/SSL Configuration
```yaml
# APISIX SSL configuration
ssl:
  cert: |
    -----BEGIN CERTIFICATE-----
    [YOUR_CERTIFICATE_CONTENT_HERE]
    -----END CERTIFICATE-----
  key: |
    -----BEGIN PRIVATE-KEY-----
    [YOUR_PRIVATE_KEY_CONTENT_HERE]
    -----END PRIVATE-KEY-----
  sni: api.violentutf.com
```

## 🔄 Backup & Recovery

### Database Backup

```bash
#!/bin/bash
# backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="violentutf"

# PostgreSQL backup
pg_dump -h postgres -U violentutf -d $DB_NAME | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# DuckDB backup (PyRIT memory)
cp /app/data/pyrit_memory.db $BACKUP_DIR/pyrit_memory_$DATE.db

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Automated Backup Schedule

```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: violentutf-backup
  namespace: violentutf
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres -U violentutf violentutf | gzip > /backup/violentutf_$(date +%Y%m%d_%H%M%S).sql.gz
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Disaster Recovery

```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Starting database restore from $BACKUP_FILE"

# Stop services
docker compose down

# Restore PostgreSQL
gunzip -c $BACKUP_FILE | docker exec -i postgres_container psql -U violentutf -d violentutf

# Restart services
docker compose up -d

echo "Database restore completed"
```

## 📈 Scaling Strategies

### Horizontal Scaling

#### 1. Load Balancer Configuration
```nginx
# nginx.conf
upstream fastapi_backend {
    least_conn;
    server fastapi1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server fastapi2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server fastapi3:8000 weight=1 max_fails=3 fail_timeout=30s;

    # Health check
    check interval=5000 rise=2 fall=3 timeout=1000;
}
```

#### 2. Auto-scaling (Kubernetes)
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: violentutf-fastapi-hpa
  namespace: violentutf
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: violentutf-fastapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling

#### 1. Read Replicas
```yaml
# PostgreSQL read replica configuration
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: violentutf
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    command: |
      postgres
      -c wal_level=replica
      -c hot_standby=on
      -c max_wal_senders=10
      -c max_replication_slots=10

  postgres-replica:
    image: postgres:15
    environment:
      PGUSER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    command: |
      bash -c "
      until ping -c 1 -W 1 postgres-primary; do
        echo 'Waiting for primary to be available...'
        sleep 1s
      done
      pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U replicator -v -P -W
      echo 'standby_mode = on' >> /var/lib/postgresql/data/postgresql.conf
      postgres
      "
```

### Performance Optimization

#### 1. Connection Pooling
```python
# FastAPI connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=300
)
```

#### 2. Caching Layer
```yaml
# Redis cache configuration
services:
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

## 🔍 Troubleshooting

### Common Deployment Issues

#### 1. Service Discovery Problems
```bash
# Check DNS resolution
docker exec fastapi_container nslookup apisix
docker exec fastapi_container curl -I http://apisix:9080/health

# Check network connectivity
docker network ls
docker network inspect vutf-network
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker exec fastapi_container pg_isready -h postgres -p 5432 -U violentutf

# Check database logs
docker logs postgres_container --tail 50

# Test manual connection
docker exec -it postgres_container psql -U violentutf -d violentutf
```

#### 3. Authentication Problems
```bash
# Verify JWT secret consistency
docker exec fastapi_container env | grep JWT_SECRET_KEY
docker exec streamlit_container env | grep JWT_SECRET_KEY

# Test Keycloak connectivity
curl -I http://localhost:8080/auth/realms/ViolentUTF
```

### Health Check Endpoints

```python
# Comprehensive health check
@app.get("/health/detailed")
async def detailed_health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Database check
    try:
        db.execute("SELECT 1")
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {e}"
        health_status["status"] = "unhealthy"

    # Keycloak check
    try:
        response = requests.get(f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}", timeout=5)
        health_status["services"]["keycloak"] = "reachable" if response.status_code == 200 else "unreachable"
    except Exception as e:
        health_status["services"]["keycloak"] = f"error: {e}"

    # PyRIT check
    try:
        from pyrit.memory import CentralMemory
        memory = CentralMemory.get_memory_instance()
        health_status["services"]["pyrit"] = "available"
    except Exception as e:
        health_status["services"]["pyrit"] = f"error: {e}"

    return health_status
```

## 📚 Migration Guides

### Version Upgrade Process

#### 1. Pre-upgrade Checklist
```bash
#!/bin/bash
# pre_upgrade_checklist.sh

echo "ViolentUTF Pre-Upgrade Checklist"
echo "================================"

# Backup databases
./backup_database.sh

# Check service health
curl -f http://localhost:9080/health || echo "APISIX gateway unhealthy"
curl -f http://localhost:8000/health || echo "FastAPI service unhealthy"

# Check disk space
df -h | grep -E "(/$|/var)"

# Check memory usage
free -h

# Verify configuration
./verify_routes.sh

echo "Pre-upgrade checks completed"
```

#### 2. Rolling Update Strategy
```bash
#!/bin/bash
# rolling_update.sh

# Update services one by one
echo "Starting rolling update..."

# Update FastAPI service
docker service update --image violentutf/fastapi:v2.0 violentutf_fastapi

# Wait for health check
sleep 30
curl -f http://localhost:9080/health

# Update APISIX
docker service update --image apache/apisix:3.3.0 violentutf_apisix

echo "Rolling update completed"
```

### Database Migration

```python
# Migration script example
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add new columns for v2.0 features"""
    op.add_column('orchestrator_configs',
                  sa.Column('config_version', sa.String(10), nullable=True))
    op.add_column('orchestrator_configs',
                  sa.Column('created_by', sa.String(255), nullable=True))

def downgrade():
    """Rollback v2.0 changes"""
    op.drop_column('orchestrator_configs', 'config_version')
    op.drop_column('orchestrator_configs', 'created_by')
```

---

**🔒 Security Notice**: Always follow security best practices for production deployments, including regular security updates, proper secret management, and network isolation.

**📋 Best Practices**:
- Use immutable infrastructure patterns
- Implement proper monitoring and alerting
- Maintain comprehensive backup strategies
- Test disaster recovery procedures regularly
- Keep all components updated with security patches
