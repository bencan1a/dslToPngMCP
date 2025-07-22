# Operations Guide

Complete operational procedures for production deployment, monitoring, and maintenance of the DSL to PNG MCP Server system.

## Table of Contents

- [Production Deployment](#production-deployment)
- [Monitoring & Alerting](#monitoring--alerting)
- [Backup & Recovery](#backup--recovery)
- [Scaling Operations](#scaling-operations)
- [Security Operations](#security-operations)
- [Maintenance Procedures](#maintenance-procedures)
- [Performance Management](#performance-management)
- [Incident Response](#incident-response)
- [Log Management](#log-management)
- [Capacity Planning](#capacity-planning)

---

## Production Deployment

### Pre-Deployment Checklist

#### Infrastructure Requirements

- [ ] **Server Resources**: Minimum 4 CPU cores, 8GB RAM, 50GB SSD
- [ ] **Network**: Load balancer configured with SSL certificates
- [ ] **DNS**: Domain records pointing to load balancer
- [ ] **Monitoring**: Prometheus, Grafana, and alerting configured
- [ ] **Backup**: Automated backup system in place
- [ ] **Security**: Firewall rules, SSL certificates, API keys configured

#### Environment Configuration

```bash
# Production environment validation
./scripts/validate-prod-env.sh

# Required environment variables
export DSL_PNG_ENVIRONMENT=production
export DSL_PNG_SECRET_KEY=$(openssl rand -hex 32)
export DSL_PNG_API_KEY=$(openssl rand -hex 16)
export DSL_PNG_ALLOWED_HOSTS='["your-domain.com"]'
export DSL_PNG_REDIS_URL=redis://redis:6379/0
export DSL_PNG_LOG_LEVEL=INFO
```

#### Security Configuration

```bash
# SSL certificate setup
sudo certbot --nginx -d your-domain.com --non-interactive --agree-tos --email admin@your-domain.com

# Firewall configuration
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct API access
sudo ufw enable

# API key generation and storage
API_KEY=$(openssl rand -hex 16)
echo "DSL_PNG_API_KEY=$API_KEY" >> /etc/dsl-png/secrets.env
chmod 600 /etc/dsl-png/secrets.env
```

### Deployment Procedure

#### 1. Blue-Green Deployment

```bash
#!/bin/bash
# blue-green-deploy.sh

# Current environment
CURRENT_ENV=$(docker compose ps --services | grep -q "blue" && echo "blue" || echo "green")
NEW_ENV=$([ "$CURRENT_ENV" = "blue" ] && echo "green" || echo "blue")

echo "Deploying to $NEW_ENV environment..."

# Deploy new version
docker compose -f docker compose.$NEW_ENV.yml up -d

# Health check
for i in {1..30}; do
    if curl -f http://localhost:8001/health; then
        echo "Health check passed"
        break
    fi
    sleep 10
done

# Switch traffic
nginx -s reload

# Stop old environment
docker compose -f docker compose.$CURRENT_ENV.yml down

echo "Deployment to $NEW_ENV completed"
```

#### 2. Rolling Deployment

```bash
#!/bin/bash
# rolling-deploy.sh

# Update each service replica individually
SERVICES=("fastapi-server" "celery-workers")

for service in "${SERVICES[@]}"; do
    replicas=$(docker service ls --filter name=$service --format "{{.Replicas}}" | cut -d'/' -f2)
    
    for ((i=1; i<=replicas; i++)); do
        echo "Updating $service replica $i..."
        docker service update --force $service
        
        # Wait for health check
        sleep 30
        if ! curl -f http://localhost:8000/health; then
            echo "Health check failed, rolling back..."
            docker service rollback $service
            exit 1
        fi
    done
done

echo "Rolling deployment completed"
```

#### 3. Verification Steps

```bash
# Post-deployment verification
./scripts/verify-deployment.sh

# 1. Health check all services
curl -f http://localhost:8000/health

# 2. Test basic functionality
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"dsl_content": "{\"width\": 400, \"height\": 300, \"elements\": []}"}'

# 3. Test rendering
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @examples/simple_button.json \
  --output test-render.png

# 4. Verify PNG output
file test-render.png | grep -q "PNG image data"

# 5. Check metrics endpoint
curl http://localhost:9090/metrics

echo "Deployment verification completed"
```

### Rollback Procedures

#### Emergency Rollback

```bash
#!/bin/bash
# emergency-rollback.sh

echo "Starting emergency rollback..."

# Get previous version
PREVIOUS_VERSION=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep dsl-png-api | sed -n '2p')

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "No previous version found!"
    exit 1
fi

# Stop current services
docker compose down

# Update image tags to previous version
sed -i "s/dsl-png-api:.*/dsl-png-api:$PREVIOUS_VERSION/" docker compose.prod.yml

# Start with previous version
docker compose -f docker compose.prod.yml up -d

# Verify rollback
sleep 30
if curl -f http://localhost:8000/health; then
    echo "Rollback successful"
else
    echo "Rollback failed - manual intervention required"
    exit 1
fi
```

---

## Monitoring & Alerting

### Metrics Collection

#### System Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'dsl-png-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
      
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

#### Application Metrics

```python
# Custom metrics for monitoring
from prometheus_client import Counter, Histogram, Gauge, Info

# Business metrics
render_requests_total = Counter(
    'dsl_render_requests_total',
    'Total render requests',
    ['status', 'complexity']
)

render_duration_seconds = Histogram(
    'dsl_render_duration_seconds',
    'Render duration in seconds',
    ['complexity'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

active_renders = Gauge(
    'dsl_active_renders',
    'Currently active render jobs'
)

browser_pool_available = Gauge(
    'dsl_browser_pool_available',
    'Available browser instances'
)

queue_size = Gauge(
    'dsl_queue_size',
    'Size of render queue'
)

# System info
app_info = Info(
    'dsl_app_info',
    'Application information'
)

app_info.info({
    'version': '1.0.0',
    'python_version': '3.11.0',
    'environment': 'production'
})
```

### Alert Configuration

#### Critical Alerts

```yaml
# alert_rules.yml
groups:
  - name: dsl-png-critical
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.job }} has been down for more than 1 minute"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests per second"
          
      - alert: DatabaseConnectionFailed
        expr: redis_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failed"
          description: "Cannot connect to Redis database"
```

#### Warning Alerts

```yaml
  - name: dsl-png-warnings
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response times detected"
          description: "95th percentile response time is {{ $value }}s"
          
      - alert: BrowserPoolLow
        expr: dsl_browser_pool_available < 2
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Browser pool running low"
          description: "Only {{ $value }} browsers available"
          
      - alert: QueueBacklog
        expr: dsl_queue_size > 50
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Render queue backlog"
          description: "{{ $value }} jobs queued for processing"
          
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
```

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_auth_username: 'alerts@your-domain.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@your-domain.com'
        subject: '[CRITICAL] DSL PNG Alert'
        body: |
          Alert: {{ .GroupLabels.alertname }}
          Summary: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}
          Description: {{ range .Alerts }}{{ .Annotations.description }}{{ end }}
    slack_configs:
      - api_url: 'your-slack-webhook-url'
        channel: '#alerts'
        title: 'Critical Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        
  - name: 'warning-alerts'
    email_configs:
      - to: 'team@your-domain.com'
        subject: '[WARNING] DSL PNG Alert'
        body: |
          Alert: {{ .GroupLabels.alertname }}
          Summary: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}
```

### Dashboard Configuration

#### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "DSL to PNG Operations Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Active Renders",
        "type": "singlestat",
        "targets": [
          {
            "expr": "dsl_active_renders",
            "legendFormat": "Active"
          }
        ]
      },
      {
        "title": "Browser Pool Status",
        "type": "singlestat",
        "targets": [
          {
            "expr": "dsl_browser_pool_available",
            "legendFormat": "Available"
          }
        ]
      }
    ]
  }
}
```

---

## Backup & Recovery

### Backup Procedures

#### Automated Daily Backup

```bash
#!/bin/bash
# daily-backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/dsl-png"
S3_BUCKET="your-backup-bucket"

echo "Starting daily backup for $DATE"

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# 1. Redis data backup
echo "Backing up Redis data..."
redis-cli BGSAVE
sleep 30
cp /var/lib/redis/dump.rdb $BACKUP_DIR/$DATE/redis-$DATE.rdb

# 2. Application configuration
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/$DATE/config-$DATE.tar.gz \
  .env \
  docker compose.prod.yml \
  nginx/ssl/ \
  prometheus/

# 3. Stored render results (last 7 days)
echo "Backing up recent render results..."
find /app/storage -name "*.png" -mtime -7 | \
  tar -czf $BACKUP_DIR/$DATE/renders-$DATE.tar.gz -T -

# 4. Application logs (last 7 days)
echo "Backing up logs..."
find /var/log/dsl-png -name "*.log" -mtime -7 | \
  tar -czf $BACKUP_DIR/$DATE/logs-$DATE.tar.gz -T -

# 5. Upload to S3
echo "Uploading to S3..."
aws s3 sync $BACKUP_DIR/$DATE/ s3://$S3_BUCKET/daily/$DATE/

# 6. Cleanup old local backups (keep 7 days)
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;

# 7. Test backup integrity
echo "Testing backup integrity..."
tar -tzf $BACKUP_DIR/$DATE/config-$DATE.tar.gz > /dev/null
tar -tzf $BACKUP_DIR/$DATE/renders-$DATE.tar.gz > /dev/null

echo "Daily backup completed successfully"
```

#### Weekly Full Backup

```bash
#!/bin/bash
# weekly-backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/dsl-png/weekly"

echo "Starting weekly full backup for $DATE"

# 1. Full system backup
tar -czf $BACKUP_DIR/full-system-$DATE.tar.gz \
  --exclude=/proc \
  --exclude=/sys \
  --exclude=/dev \
  --exclude=/tmp \
  --exclude=/backup \
  /

# 2. Docker images backup
docker save dsl-png-api:latest dsl-png-worker:latest | \
  gzip > $BACKUP_DIR/docker-images-$DATE.tar.gz

# 3. Database snapshot
pg_dump dsl_png_db > $BACKUP_DIR/postgres-$DATE.sql

# 4. Upload to S3
aws s3 sync $BACKUP_DIR/ s3://$S3_BUCKET/weekly/

echo "Weekly full backup completed"
```

### Recovery Procedures

#### Disaster Recovery

```bash
#!/bin/bash
# disaster-recovery.sh

echo "Starting disaster recovery procedure..."

# 1. Stop all services
docker compose down
systemctl stop nginx
systemctl stop redis

# 2. Restore Redis data
echo "Restoring Redis data..."
LATEST_BACKUP=$(aws s3 ls s3://$S3_BUCKET/daily/ | sort | tail -n 1 | awk '{print $2}')
aws s3 cp s3://$S3_BUCKET/daily/$LATEST_BACKUP/redis-*.rdb /var/lib/redis/dump.rdb
chown redis:redis /var/lib/redis/dump.rdb

# 3. Restore configuration
echo "Restoring configuration..."
aws s3 cp s3://$S3_BUCKET/daily/$LATEST_BACKUP/config-*.tar.gz /tmp/
tar -xzf /tmp/config-*.tar.gz

# 4. Restore Docker images
echo "Restoring Docker images..."
aws s3 cp s3://$S3_BUCKET/weekly/docker-images-*.tar.gz /tmp/
docker load < /tmp/docker-images-*.tar.gz

# 5. Start services
echo "Starting services..."
systemctl start redis
docker compose up -d
systemctl start nginx

# 6. Verify recovery
echo "Verifying recovery..."
sleep 60
if curl -f http://localhost:8000/health; then
    echo "Disaster recovery completed successfully"
else
    echo "Recovery verification failed"
    exit 1
fi
```

#### Point-in-Time Recovery

```bash
#!/bin/bash
# point-in-time-recovery.sh

TARGET_DATE=$1
if [ -z "$TARGET_DATE" ]; then
    echo "Usage: $0 YYYYMMDD"
    exit 1
fi

echo "Performing point-in-time recovery to $TARGET_DATE"

# 1. Stop services
docker compose down

# 2. Restore from specific date
aws s3 cp s3://$S3_BUCKET/daily/$TARGET_DATE/redis-$TARGET_DATE.rdb /var/lib/redis/dump.rdb
aws s3 cp s3://$S3_BUCKET/daily/$TARGET_DATE/config-$TARGET_DATE.tar.gz /tmp/
tar -xzf /tmp/config-$TARGET_DATE.tar.gz

# 3. Start services
docker compose up -d

echo "Point-in-time recovery to $TARGET_DATE completed"
```

---

## Scaling Operations

### Horizontal Scaling

#### Scale Up Procedure

```bash
#!/bin/bash
# scale-up.sh

SERVICE=$1
REPLICAS=$2

if [ -z "$SERVICE" ] || [ -z "$REPLICAS" ]; then
    echo "Usage: $0 <service> <replicas>"
    exit 1
fi

echo "Scaling $SERVICE to $REPLICAS replicas..."

# Docker Swarm scaling
docker service scale $SERVICE=$REPLICAS

# Wait for scaling to complete
for i in {1..60}; do
    CURRENT_REPLICAS=$(docker service ls --filter name=$SERVICE --format "{{.Replicas}}" | cut -d'/' -f1)
    if [ "$CURRENT_REPLICAS" -eq "$REPLICAS" ]; then
        echo "Scaling completed successfully"
        break
    fi
    sleep 5
done

# Verify health after scaling
sleep 30
if curl -f http://localhost:8000/health; then
    echo "Health check passed after scaling"
else
    echo "Health check failed - consider rolling back"
fi
```

#### Auto-scaling Based on Metrics

```python
# auto-scaler.py
import asyncio
import docker
from prometheus_api_client import PrometheusConnect

class AutoScaler:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.prometheus = PrometheusConnect(url="http://localhost:9090")
        
    async def monitor_and_scale(self):
        """Monitor metrics and auto-scale services"""
        while True:
            # Get current metrics
            cpu_usage = self.get_avg_cpu_usage()
            memory_usage = self.get_avg_memory_usage()
            queue_size = self.get_queue_size()
            response_time = self.get_avg_response_time()
            
            # Scale API servers based on CPU and response time
            if cpu_usage > 70 or response_time > 5:
                await self.scale_service("fastapi-server", "up")
            elif cpu_usage < 30 and response_time < 2:
                await self.scale_service("fastapi-server", "down")
                
            # Scale workers based on queue size
            if queue_size > 20:
                await self.scale_service("celery-workers", "up")
            elif queue_size < 5:
                await self.scale_service("celery-workers", "down")
                
            await asyncio.sleep(60)  # Check every minute
            
    async def scale_service(self, service_name: str, direction: str):
        """Scale service up or down"""
        service = self.docker_client.services.get(service_name)
        current_replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']
        
        if direction == "up":
            new_replicas = min(current_replicas + 1, 10)  # Max 10 replicas
        else:
            new_replicas = max(current_replicas - 1, 1)   # Min 1 replica
            
        if new_replicas != current_replicas:
            service.scale(new_replicas)
            print(f"Scaled {service_name} from {current_replicas} to {new_replicas}")
```

### Vertical Scaling

#### Resource Optimization

```bash
#!/bin/bash
# optimize-resources.sh

echo "Optimizing container resources..."

# Update service resource limits
docker service update \
  --limit-cpu="1.0" \
  --limit-memory="2G" \
  --reserve-cpu="0.5" \
  --reserve-memory="1G" \
  dsl-png-api

docker service update \
  --limit-cpu="2.0" \
  --limit-memory="4G" \
  --reserve-cpu="1.0" \
  --reserve-memory="2G" \
  dsl-png-workers

# Update browser pool settings
docker service update \
  --env-add DSL_PNG_BROWSER_POOL_SIZE=8 \
  --limit-memory="8G" \
  dsl-png-browsers

echo "Resource optimization completed"
```

---

## Security Operations

### Security Monitoring

#### Security Event Detection

```bash
#!/bin/bash
# security-monitor.sh

LOG_FILE="/var/log/dsl-png/security.log"

# Monitor for suspicious activity
tail -f /var/log/nginx/access.log | while read line; do
    # Check for potential attacks
    if echo "$line" | grep -qE "(sql|script|iframe|<|>|javascript:|data:)"; then
        echo "$(date): Potential injection attempt: $line" >> $LOG_FILE
        # Send alert
        curl -X POST "your-webhook-url" \
          -H "Content-Type: application/json" \
          -d '{"text": "Security alert: Potential injection attempt detected"}'
    fi
    
    # Check for brute force attempts
    IP=$(echo "$line" | awk '{print $1}')
    if [ "$(grep -c "$IP" /tmp/recent_requests.log)" -gt 100 ]; then
        echo "$(date): Potential brute force from $IP" >> $LOG_FILE
        # Block IP
        sudo ufw insert 1 deny from $IP
    fi
done
```

#### Security Audit Script

```bash
#!/bin/bash
# security-audit.sh

echo "Starting security audit..."

# 1. Check for unauthorized access
echo "Checking access logs..."
grep -E "40[0-9]|50[0-9]" /var/log/nginx/access.log | tail -20

# 2. Verify SSL certificates
echo "Checking SSL certificates..."
openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -noout -dates

# 3. Check for exposed endpoints
echo "Checking for exposed endpoints..."
nmap -sS -p 1-65535 localhost

# 4. Verify file permissions
echo "Checking file permissions..."
find /app -type f -perm /o+w -ls

# 5. Check for security updates
echo "Checking for security updates..."
apt list --upgradable | grep -i security

# 6. Verify Docker security
echo "Checking Docker security..."
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/docker-bench-security

echo "Security audit completed"
```

### SSL Certificate Management

#### Automatic Certificate Renewal

```bash
#!/bin/bash
# renew-certificates.sh

echo "Checking SSL certificate renewal..."

# Check certificate expiry
EXPIRY_DATE=$(openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    echo "Certificate expires in $DAYS_UNTIL_EXPIRY days, renewing..."
    
    # Renew certificate
    certbot renew --nginx --non-interactive
    
    # Reload nginx
    nginx -s reload
    
    # Verify renewal
    NEW_EXPIRY_DATE=$(openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -noout -enddate | cut -d= -f2)
    echo "Certificate renewed. New expiry: $NEW_EXPIRY_DATE"
else
    echo "Certificate is valid for $DAYS_UNTIL_EXPIRY more days"
fi
```

---

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Maintenance

```bash
#!/bin/bash
# daily-maintenance.sh

echo "Starting daily maintenance..."

# 1. Clean up temporary files
find /tmp -type f -mtime +1 -delete
find /app/tmp -type f -mtime +1 -delete

# 2. Rotate logs
logrotate /etc/logrotate.d/dsl-png

# 3. Clean up old render results
find /app/storage -name "*.png" -mtime +30 -delete

# 4. Update system packages
apt update && apt upgrade -y

# 5. Clean up Docker resources
docker system prune -f
docker volume prune -f

# 6. Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
    # Send alert
fi

# 7. Verify service health
curl -f http://localhost:8000/health || echo "Health check failed"

echo "Daily maintenance completed"
```

#### Weekly Maintenance

```bash
#!/bin/bash
# weekly-maintenance.sh

echo "Starting weekly maintenance..."

# 1. Full backup (already implemented above)
./scripts/weekly-backup.sh

# 2. Security updates
apt update
apt list --upgradable | grep -i security
apt upgrade -y

# 3. Certificate check
./scripts/renew-certificates.sh

# 4. Performance analysis
echo "Generating performance report..."
docker stats --no-stream > /tmp/performance-$(date +%Y%m%d).txt

# 5. Log analysis
echo "Analyzing logs for errors..."
grep -i error /var/log/dsl-png/*.log | tail -50 > /tmp/errors-$(date +%Y%m%d).txt

# 6. Database maintenance
redis-cli BGREWRITEAOF

# 7. Container health check
docker inspect $(docker ps -q) | jq '.[].State.Health.Status'

echo "Weekly maintenance completed"
```

#### Monthly Maintenance

```bash
#!/bin/bash
# monthly-maintenance.sh

echo "Starting monthly maintenance..."

# 1. Full security audit
./scripts/security-audit.sh > /tmp/security-audit-$(date +%Y%m).txt

# 2. Performance tuning review
echo "Reviewing performance metrics..."
# Generate monthly performance report from Prometheus

# 3. Capacity planning analysis
echo "Analyzing capacity trends..."
# Review growth trends and plan for scaling

# 4. Dependency updates
echo "Checking for dependency updates..."
pip list --outdated > /tmp/pip-outdated-$(date +%Y%m).txt

# 5. Configuration review
echo "Reviewing configuration..."
# Check for configuration drift

# 6. Disaster recovery test
echo "Testing disaster recovery procedures..."
./scripts/test-backup-restore.sh

echo "Monthly maintenance completed"
```

### Update Procedures

#### Application Updates

```bash
#!/bin/bash
# update-application.sh

NEW_VERSION=$1
if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Updating application to version $NEW_VERSION..."

# 1. Create backup
./scripts/daily-backup.sh

# 2. Pull new images
docker pull dsl-png-api:$NEW_VERSION
docker pull dsl-png-worker:$NEW_VERSION

# 3. Update docker compose with new version
sed -i "s/dsl-png-api:.*/dsl-png-api:$NEW_VERSION/" docker compose.prod.yml
sed -i "s/dsl-png-worker:.*/dsl-png-worker:$NEW_VERSION/" docker compose.prod.yml

# 4. Perform rolling update
./scripts/rolling-deploy.sh

# 5. Verify update
sleep 60
if curl -f http://localhost:8000/health; then
    echo "Update to $NEW_VERSION completed successfully"
else
    echo "Update failed, rolling back..."
    ./scripts/emergency-rollback.sh
fi
```

#### System Updates

```bash
#!/bin/bash
# update-system.sh

echo "Starting system update..."

# 1. Update package lists
apt update

# 2. Check for security updates
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -c security)
if [ $SECURITY_UPDATES -gt 0 ]; then
    echo "Found $SECURITY_UPDATES security updates"
    apt upgrade -y
    
    # Check if reboot is required
    if [ -f /var/run/reboot-required ]; then
        echo "Reboot required for security updates"
        # Schedule maintenance window for reboot
    fi
fi

# 3. Update Docker
if docker version --format '{{.Server.Version}}' | grep -q "20.10"; then
    echo "Docker update available"
    # Update Docker following safe procedures
fi

echo "System update completed"
```

---

## Performance Management

### Performance Monitoring

#### Real-time Performance Dashboard

```python
# performance-monitor.py
import asyncio
import psutil
import docker
from prometheus_api_client import PrometheusConnect

class PerformanceMonitor:
    def __init__(self):
        self.prometheus = PrometheusConnect(url="http://localhost:9090")
        self.docker_client = docker.from_env()
        
    async def collect_metrics(self):
        """Collect real-time performance metrics"""
        while True:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Application metrics
            response_time = self.get_avg_response_time()
            error_rate = self.get_error_rate()
            active_connections = self.get_active_connections()
            
            # Print performance summary
            print(f"""
Performance Summary:
- CPU Usage: {cpu_percent}%
- Memory Usage: {memory.percent}%
- Disk Usage: {disk.percent}%
- Avg Response Time: {response_time}s
- Error Rate: {error_rate}%
- Active Connections: {active_connections}
            """)
            
            # Check for performance issues
            if cpu_percent > 80:
                await self.alert("High CPU usage detected")
            if memory.percent > 85:
                await self.alert("High memory usage detected")
            if response_time > 10:
                await self.alert("Slow response times detected")
                
            await asyncio.sleep(60)
```

#### Performance Optimization

```bash
#!/bin/bash
# optimize-performance.sh

echo "Starting performance optimization..."

# 1. Optimize browser pool
CURRENT_LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)
if (( $(echo "$CURRENT_LOAD > 2.0" | bc -l) )); then
    # Reduce browser pool size under high load
    docker service update --env-add DSL_PNG_BROWSER_POOL_SIZE=3 dsl-png-browsers
else
    # Increase browser pool size under low load
    docker service update --env-add DSL_PNG_BROWSER_POOL_SIZE=6 dsl-png-browsers
fi

# 2. Optimize Redis memory
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 3. Optimize Nginx
nginx -s reload

# 4. Clean up old processes
pkill -f "defunct"

echo "Performance optimization completed"
```

---

## Incident Response

### Incident Response Procedures

#### Incident Classification

| Severity | Definition | Response Time | Escalation |
|----------|------------|---------------|------------|
| **P0 - Critical** | Service completely down | 15 minutes | Immediate |
| **P1 - High** | Major functionality affected | 1 hour | 2 hours |
| **P2 - Medium** | Minor functionality affected | 4 hours | 24 hours |
| **P3 - Low** | Cosmetic or minor issues | 24 hours | 72 hours |

#### Incident Response Playbook

```bash
#!/bin/bash
# incident-response.sh

SEVERITY=$1
DESCRIPTION=$2

echo "Starting incident response for $SEVERITY incident..."

# 1. Immediate assessment
curl -f http://localhost:8000/health > /tmp/health-check.txt
docker ps --format "table {{.Names}}\t{{.Status}}" > /tmp/container-status.txt

# 2. Collect diagnostics
./scripts/collect-diagnostics.sh

# 3. Check recent changes
git log --oneline -10 > /tmp/recent-changes.txt
docker service ls > /tmp/service-status.txt

# 4. Send initial alert
curl -X POST "your-incident-webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "'$SEVERITY'",
    "description": "'$DESCRIPTION'",
    "status": "investigating",
    "timestamp": "'$(date -Iseconds)'"
  }'

# 5. Start monitoring
./scripts/enhanced-monitoring.sh &

echo "Incident response initiated"
```

#### Common Incident Scenarios

**1. Service Unavailable**

```bash
# service-down-response.sh
echo "Service down incident response..."

# Check if containers are running
if ! docker ps | grep -q dsl-png-api; then
    echo "API container down, restarting..."
    docker compose restart fastapi-server
fi

# Check load balancer
nginx -t && nginx -s reload

# Check dependencies
redis-cli ping || systemctl restart redis

# Verify recovery
sleep 30
curl -f http://localhost:8000/health
```

**2. High Response Times**

```bash
# slow-response-incident.sh
echo "High response time incident response..."

# Check system resources
top -n 1 -b | head -20
free -h
df -h

# Check browser pool
docker stats --no-stream | grep browser

# Scale up if needed
docker service scale fastapi-server=6
docker service scale celery-workers=8

# Clear cache if corrupted
redis-cli FLUSHDB
```

**3. Memory Issues**

```bash
# memory-incident.sh
echo "Memory issue incident response..."

# Identify memory consumers
ps aux --sort=-%mem | head -10

# Restart memory-heavy services
docker compose restart playwright-browsers

# Clean up temporary files
find /tmp -type f -delete
find /app/tmp -type f -delete

# Adjust memory limits
docker service update --limit-memory=4G dsl-png-browsers
```

---

## Log Management

### Log Configuration

#### Centralized Logging

```yaml
# docker compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
      
  logstash:
    image: logstash:7.14.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch
    ports:
      - "5044:5044"
      
  kibana:
    image: kibana:7.14.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    ports:
      - "5601:5601"
      
  filebeat:
    image: elastic/filebeat:7.14.0
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash

volumes:
  elasticsearch_data:
```

#### Log Rotation

```bash
# /etc/logrotate.d/dsl-png
/var/log/dsl-png/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        docker kill --signal="USR1" $(docker ps --filter name=dsl-png --format "{{.ID}}")
    endscript
}
```

### Log Analysis

#### Error Analysis Script

```bash
#!/bin/bash
# analyze-logs.sh

LOG_DIR="/var/log/dsl-png"
REPORT_FILE="/tmp/log-analysis-$(date +%Y%m%d).txt"

echo "DSL PNG Log Analysis Report - $(date)" > $REPORT_FILE
echo "================================================" >> $REPORT_FILE

# 1. Error frequency
echo "Error Frequency (last 24 hours):" >> $REPORT_FILE
grep -h "ERROR" $LOG_DIR/*.log | \
  grep "$(date +%Y-%m-%d)" | \
  cut -d' ' -f3- | \
  sort | uniq -c | sort -nr >> $REPORT_FILE

# 2. Performance issues
echo -e "\nSlow Requests (>5 seconds):" >> $REPORT_FILE
grep -h "response_time" $LOG_DIR/*.log | \
  awk '$NF > 5 {print}' | \
  tail -20 >> $REPORT_FILE

# 3. Top IP addresses
echo -e "\nTop Client IPs:" >> $REPORT_FILE
grep -h "client_ip" $LOG_DIR/*.log | \
  awk '{print $NF}' | \
  sort | uniq -c | sort -nr | head -10 >> $REPORT_FILE

echo "Log analysis completed: $REPORT_FILE"
```

---

## Capacity Planning

### Growth Projections

#### Capacity Monitoring

```python
# capacity-planner.py
import pandas as pd
from prometheus_api_client import PrometheusConnect

class CapacityPlanner:
    def __init__(self):
        self.prometheus = PrometheusConnect(url="http://localhost:9090")
        
    def analyze_growth_trends(self):
        """Analyze growth trends for capacity planning"""
        
        # Get 30 days of metrics
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        # Request volume trend
        request_data = self.prometheus.get_metric_range_data(
            metric_name="http_requests_total",
            start_time=start_time,
            end_time=end_time
        )
        
        # Resource usage trends
        cpu_data = self.prometheus.get_metric_range_data(
            metric_name="rate(cpu_usage_seconds_total[5m])",
            start_time=start_time,
            end_time=end_time
        )
        
        memory_data = self.prometheus.get_metric_range_data(
            metric_name="memory_usage_bytes",
            start_time=start_time,
            end_time=end_time
        )
        
        # Calculate growth rates
        request_growth = self.calculate_growth_rate(request_data)
        cpu_growth = self.calculate_growth_rate(cpu_data)
        memory_growth = self.calculate_growth_rate(memory_data)
        
        # Project future capacity needs
        return {
            "request_growth_rate": request_growth,
            "cpu_growth_rate": cpu_growth,
            "memory_growth_rate": memory_growth,
            "projected_scaling_date": self.calculate_scaling_date(request_growth),
            "recommended_actions": self.get_scaling_recommendations(
                request_growth, cpu_growth, memory_growth
            )
        }
```

#### Scaling Recommendations

```bash
#!/bin/bash
# capacity-recommendations.sh

echo "Generating capacity recommendations..."

# Current utilization
CPU_UTIL=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
MEM_UTIL=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
DISK_UTIL=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "Current Utilization:"
echo "- CPU: ${CPU_UTIL}%"
echo "- Memory: ${MEM_UTIL}%"
echo "- Disk: ${DISK_UTIL}%"

# Growth rate analysis (simplified)
REQUEST_RATE=$(grep "request" /var/log/dsl-png/api.log | wc -l)
LAST_WEEK_RATE=$(grep "request" /var/log/dsl-png/api.log.1 | wc -l)
GROWTH_RATE=$(echo "scale=2; ($REQUEST_RATE - $LAST_WEEK_RATE) / $LAST_WEEK_RATE * 100" | bc)

echo -e "\nGrowth Analysis:"
echo "- Weekly request growth: ${GROWTH_RATE}%"

# Recommendations
if (( $(echo "$CPU_UTIL > 70" | bc -l) )); then
    echo -e "\nRecommendation: Scale up CPU resources"
    echo "- Add 2 more API server replicas"
    echo "- Consider upgrading to higher CPU instances"
fi

if (( $(echo "$MEM_UTIL > 80" | bc -l) )); then
    echo -e "\nRecommendation: Scale up memory resources"
    echo "- Increase memory limits for browser containers"
    echo "- Add more worker replicas"
fi

if (( $(echo "$GROWTH_RATE > 20" | bc -l) )); then
    echo -e "\nRecommendation: Prepare for rapid scaling"
    echo "- Set up auto-scaling policies"
    echo "- Plan additional infrastructure"
fi
```

This comprehensive Operations Guide provides the necessary procedures and tools for successfully operating the DSL to PNG MCP Server in production environments. Regular execution of these procedures will ensure high availability, performance, and security of the system.