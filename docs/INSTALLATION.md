# Installation Guide

Complete installation and setup guide for the DSL to PNG MCP Server covering development, testing, and production environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Security Setup](#security-setup)
- [Performance Tuning](#performance-tuning)
- [Verification](#verification)

---

## System Requirements

### Minimum Requirements

| Component | Requirement | Recommended |
|-----------|-------------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 10 GB | 50+ GB |
| **OS** | Linux/macOS/Windows | Linux (Ubuntu 20.04+) |
| **Docker** | 20.10+ | Latest stable |
| **Python** | 3.9+ | 3.11+ |
| **Node.js** | 16+ | 18+ (for MCP clients) |

### Production Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Storage** | 50 GB SSD | 200+ GB SSD |
| **Network** | 100 Mbps | 1 Gbps |
| **Load Balancer** | Optional | Required |

### Dependencies

- **Docker & Docker Compose**: Container orchestration
- **Redis**: Caching and message queue
- **Playwright**: Browser automation
- **FastAPI**: REST API framework
- **Celery**: Background task processing

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/dslToPngMCP.git
cd dslToPngMCP
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Start with Docker

```bash
# Development
docker compose up -d

# Production
docker compose -f docker compose.prod.yaml up -d
```

### 4. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Test render
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"dsl_content": "{\"width\": 400, \"height\": 300, \"elements\": []}"}'
```

---

## Development Setup

### Option 1: Docker Development (Recommended)

#### Prerequisites

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker compose
sudo chmod +x /usr/local/bin/docker compose
```

#### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/your-org/dslToPngMCP.git
cd dslToPngMCP

# 2. Create environment file
cp .env.example .env

# 3. Edit development configuration
cat > .env << EOF
# Application
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_LOG_LEVEL=DEBUG

# Services
DSL_PNG_HOST=0.0.0.0
DSL_PNG_PORT=8000
DSL_PNG_MCP_PORT=3001

# Redis
DSL_PNG_REDIS_URL=redis://redis:6379/0
DSL_PNG_CELERY_BROKER_URL=redis://redis:6379/1

# Browser
DSL_PNG_PLAYWRIGHT_HEADLESS=true
DSL_PNG_BROWSER_POOL_SIZE=3

# Security (dev only)
DSL_PNG_SECRET_KEY=dev-secret-key
DSL_PNG_ALLOWED_HOSTS=["*"]
EOF

# 4. Start development stack
docker compose up -d

# 5. View logs
docker compose logs -f
```

#### Development Commands

```bash
# Start services
make dev-start
# or
docker compose up -d

# Stop services
make dev-stop
# or
docker compose down

# View logs
make dev-logs
# or
docker compose logs -f

# Rebuild after code changes
make dev-rebuild
# or
docker compose up -d --build

# Run tests
make test
# or
docker compose -f docker compose.test.yml up --abort-on-container-exit

# Access shell
docker compose exec fastapi-server bash
```

### Option 2: Local Development

#### Prerequisites

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Redis
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Install system dependencies
sudo apt install -y \
  build-essential \
  curl \
  git \
  libmagic1 \
  libpq-dev \
  pkg-config
```

#### Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements/dev.txt

# Install Playwright browsers
playwright install
playwright install-deps
```

#### Local Services

```bash
# Terminal 1: Start Redis (if not running as service)
redis-server

# Terminal 2: Start Celery worker
celery -A src.core.queue.tasks worker --loglevel=info

# Terminal 3: Start FastAPI server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Start MCP server
python -m src.mcp_server.server
```

#### Environment Variables

```bash
# Create local environment
cat > .env << EOF
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_HOST=127.0.0.1
DSL_PNG_PORT=8000
DSL_PNG_REDIS_URL=redis://localhost:6379/0
DSL_PNG_CELERY_BROKER_URL=redis://localhost:6379/1
DSL_PNG_STORAGE_PATH=./storage
DSL_PNG_TEMP_PATH=./tmp
EOF
```

---

## Production Deployment

### Option 1: Docker Production

#### Prerequisites

```bash
# Production server setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker compose nginx certbot

# Configure firewall
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

#### Deployment Steps

```bash
# 1. Clone repository
git clone https://github.com/your-org/dslToPngMCP.git
cd dslToPngMCP

# 2. Create production environment
cat > .env.prod << EOF
# Application
DSL_PNG_ENVIRONMENT=production
DSL_PNG_DEBUG=false
DSL_PNG_LOG_LEVEL=INFO
DSL_PNG_HOST=0.0.0.0
DSL_PNG_PORT=8000

# Security
DSL_PNG_SECRET_KEY=$(openssl rand -hex 32)
DSL_PNG_API_KEY=$(openssl rand -hex 16)
DSL_PNG_ALLOWED_HOSTS=["your-domain.com"]

# Database
DSL_PNG_REDIS_URL=redis://redis:6379/0
DSL_PNG_CELERY_BROKER_URL=redis://redis:6379/1
DSL_PNG_REDIS_MAX_CONNECTIONS=20

# Performance
DSL_PNG_WORKERS=4
DSL_PNG_BROWSER_POOL_SIZE=8
DSL_PNG_CELERY_TASK_TIMEOUT=600

# Storage
DSL_PNG_STORAGE_PATH=/app/storage
DSL_PNG_TEMP_PATH=/app/tmp
DSL_PNG_CACHE_TTL=7200

# Monitoring
DSL_PNG_ENABLE_METRICS=true
DSL_PNG_METRICS_PORT=9090
EOF

# 3. Create required directories
sudo mkdir -p /var/lib/dsl-png/{storage,tmp,logs}
sudo chown -R 1000:1000 /var/lib/dsl-png

# 4. Deploy with production compose
docker compose -f docker compose.prod.yaml up -d

# 5. Verify deployment
curl http://localhost:8000/health
```

#### Production Docker Compose

The production setup includes:

- **nginx-proxy**: Load balancer and SSL termination
- **fastapi-server**: API server (2 replicas)
- **mcp-server**: MCP protocol server
- **celery-workers**: Background workers (4 replicas)
- **playwright-browsers**: Browser pool service
- **redis**: Cache and message queue
- **monitoring**: Prometheus metrics (optional)

### Option 2: Kubernetes Deployment

#### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/
```

#### Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dsl-png

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dsl-png-config
  namespace: dsl-png
data:
  DSL_PNG_ENVIRONMENT: "production"
  DSL_PNG_DEBUG: "false"
  DSL_PNG_LOG_LEVEL: "INFO"
  DSL_PNG_REDIS_URL: "redis://redis:6379/0"

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dsl-png-api
  namespace: dsl-png
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dsl-png-api
  template:
    metadata:
      labels:
        app: dsl-png-api
    spec:
      containers:
      - name: api
        image: dsl-png:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dsl-png-config
        - secretRef:
            name: dsl-png-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n dsl-png
kubectl logs -f deployment/dsl-png-api -n dsl-png
```

---

## Configuration

### Environment Variables

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DSL_PNG_ENVIRONMENT` | `development` | Environment mode |
| `DSL_PNG_DEBUG` | `true` | Debug mode |
| `DSL_PNG_LOG_LEVEL` | `INFO` | Logging level |
| `DSL_PNG_HOST` | `0.0.0.0` | Server bind host |
| `DSL_PNG_PORT` | `8000` | Server port |

#### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DSL_PNG_WORKERS` | `1` | FastAPI worker processes |
| `DSL_PNG_BROWSER_POOL_SIZE` | `5` | Browser instances |
| `DSL_PNG_RENDER_TIMEOUT` | `30` | Render timeout (seconds) |
| `DSL_PNG_CACHE_TTL` | `3600` | Cache TTL (seconds) |

#### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DSL_PNG_SECRET_KEY` | `dev-secret-key` | Session secret |
| `DSL_PNG_API_KEY` | `None` | API authentication key |
| `DSL_PNG_ALLOWED_HOSTS` | `["*"]` | CORS allowed hosts |

### Configuration Files

#### Docker Override

Create `docker compose.override.yml` for local customization:

```yaml
version: '3.8'
services:
  fastapi-server:
    environment:
      - DSL_PNG_LOG_LEVEL=DEBUG
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src:ro
      - ./storage:/app/storage

  redis:
    ports:
      - "6379:6379"
```

#### Nginx Configuration

For production with custom domain:

```nginx
# /etc/nginx/sites-available/dsl-png
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long renders
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

---

## Security Setup

### SSL/TLS Configuration

#### Using Certbot (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Using Custom Certificates

```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/dsl-png

# Copy certificates
sudo cp your-domain.crt /etc/ssl/dsl-png/
sudo cp your-domain.key /etc/ssl/dsl-png/
sudo chmod 600 /etc/ssl/dsl-png/your-domain.key
```

### API Security

#### API Key Setup

```bash
# Generate API key
API_KEY=$(openssl rand -hex 16)
echo "DSL_PNG_API_KEY=$API_KEY" >> .env

# Use in requests
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/health
```

#### Rate Limiting

Configure in environment:

```bash
# Rate limiting (requests per minute)
DSL_PNG_RATE_LIMIT_RENDER=10
DSL_PNG_RATE_LIMIT_VALIDATE=100
DSL_PNG_RATE_LIMIT_STATUS=200
```

### Firewall Configuration

```bash
# UFW rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct API access
sudo ufw enable

# Verify rules
sudo ufw status
```

---

## Performance Tuning

### System Optimization

#### Memory Settings

```bash
# Increase shared memory for browsers
echo 'tmpfs /dev/shm tmpfs defaults,noatime,nosuid,nodev,noexec,relatime,size=2G 0 0' >> /etc/fstab

# Kernel parameters
cat >> /etc/sysctl.conf << EOF
# Network optimization
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535

# Memory optimization  
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF

sysctl -p
```

#### File Descriptors

```bash
# Increase file descriptor limits
cat >> /etc/security/limits.conf << EOF
* soft nofile 65535
* hard nofile 65535
EOF

# For systemd services
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/override.conf << EOF
[Service]
LimitNOFILE=65535
EOF

systemctl daemon-reload
systemctl restart docker
```

### Application Tuning

#### Browser Pool Optimization

```bash
# Environment settings for production
DSL_PNG_BROWSER_POOL_SIZE=8        # 2x CPU cores
DSL_PNG_PLAYWRIGHT_TIMEOUT=60000   # 60 seconds
DSL_PNG_RENDER_TIMEOUT=120         # 2 minutes
```

#### Worker Configuration

```bash
# Celery workers
DSL_PNG_CELERY_WORKERS=4           # CPU cores
DSL_PNG_CELERY_CONCURRENCY=2       # Per worker
DSL_PNG_CELERY_MAX_TASKS_PER_CHILD=1000

# FastAPI workers
DSL_PNG_WORKERS=4                  # CPU cores
DSL_PNG_WORKER_CONNECTIONS=1000    # Per worker
```

#### Redis Tuning

```bash
# Redis configuration
cat > /etc/redis/redis.conf << EOF
# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Network
tcp-keepalive 300
timeout 0

# Performance
tcp-backlog 511
databases 16
EOF

systemctl restart redis
```

### Monitoring Setup

#### Prometheus Metrics

```bash
# Enable metrics in environment
DSL_PNG_ENABLE_METRICS=true
DSL_PNG_METRICS_PORT=9090

# Access metrics
curl http://localhost:9090/metrics
```

#### Log Management

```bash
# Configure log rotation
cat > /etc/logrotate.d/dsl-png << EOF
/var/log/dsl-png/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

---

## Verification

### Health Checks

#### System Health

```bash
# Check service status
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": true,
  "redis": true,
  "browser_pool": true,
  "celery": true,
  "active_tasks": 0,
  "queue_size": 0
}
```

#### Component Testing

```bash
# Test Redis connectivity
redis-cli ping
# Expected: PONG

# Test browser automation
docker compose exec playwright-browsers playwright --version
# Expected: Version 1.x.x

# Test Celery workers
celery -A src.core.queue.tasks inspect active
# Expected: Active task list
```

### Functional Testing

#### Basic DSL Render

```bash
# Create test DSL
cat > test-button.json << EOF
{
  "width": 300,
  "height": 150,
  "elements": [
    {
      "type": "button",
      "layout": {"x": 100, "y": 50, "width": 100, "height": 50},
      "style": {"background": "#007bff", "color": "white"},
      "label": "Test Button"
    }
  ]
}
EOF

# Test validation
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @test-button.json

# Test rendering
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @test-button.json \
  --output test-button.png

# Verify PNG file
file test-button.png
# Expected: PNG image data
```

#### Performance Testing

```bash
# Install load testing tool
pip install locust

# Create load test
cat > locustfile.py << EOF
from locust import HttpUser, task, between

class DSLUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task(3)
    def validate_dsl(self):
        dsl = {
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "text",
                    "text": "Load test",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 50}
                }
            ]
        }
        self.client.post("/validate", json={"dsl_content": str(dsl)})
EOF

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Troubleshooting Installation

#### Common Issues

1. **Port conflicts**:
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Use different port
   DSL_PNG_PORT=8080
   ```

2. **Permission errors**:
   ```bash
   # Fix Docker permissions
   sudo usermod -aG docker $USER
   newgrp docker
   
   # Fix storage permissions
   sudo chown -R $USER:$USER ./storage ./tmp
   ```

3. **Browser installation fails**:
   ```bash
   # Install browser dependencies
   sudo apt install -y \
     libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
     libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
   
   # Reinstall browsers
   playwright install --force
   ```

4. **Memory issues**:
   ```bash
   # Reduce browser pool size
   DSL_PNG_BROWSER_POOL_SIZE=2
   
   # Enable swap
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## Next Steps

After successful installation:

1. **Configure monitoring**: Set up log aggregation and metrics
2. **Set up backups**: Configure automated data backups
3. **Security hardening**: Review security configurations
4. **Load testing**: Validate performance under load
5. **Documentation**: Update deployment documentation

For detailed operational procedures, see the [Operations Guide](./OPERATIONS.md).

For development workflows, see the [Contributing Guide](../CONTRIBUTING.md).