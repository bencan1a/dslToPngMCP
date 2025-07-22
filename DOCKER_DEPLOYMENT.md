# Docker Deployment Guide

Complete guide for deploying the DSL to PNG MCP Server using Docker containers with production-ready multi-container orchestration.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Backup & Recovery](#backup--recovery)

## 🏗️ Overview

The DSL to PNG MCP Server uses a multi-container Docker architecture with the following services:

- **nginx-proxy**: Reverse proxy and load balancer
- **mcp-server**: MCP protocol handling service
- **fastapi-server**: REST API service (2 replicas)
- **celery-workers**: Background task workers (4 replicas)
- **playwright-browsers**: Browser pool service
- **redis**: Cache and message queue

## 🔧 Architecture

### Service Communication Flow

```
Internet → Nginx Proxy → FastAPI Servers → MCP Server
                ↓              ↓
            Static Files   Redis Queue → Celery Workers → Playwright Browsers
```

### Network Topology

- **Frontend Network** (`172.30.0.0/24`): External access and nginx proxy
- **Backend Network** (`172.31.0.0/24`): Internal API communication (isolated)
- **Browser Network** (`172.32.0.0/24`): Playwright browser pool (isolated)

### Volume Strategy

#### Hot Storage (Fast Access)
- **PNG Storage**: `/opt/dsl-png/storage/png` - Recently generated PNGs
- **Redis Data**: `/opt/dsl-png/data/redis` - Cache and queue persistence

#### Warm Storage (Archival)
- **Logs**: `/opt/dsl-png/logs` - Application logs with rotation
- **Backups**: `/opt/dsl-png/backups` - System backups

## 📋 Prerequisites

### System Requirements

```bash
# Minimum requirements
CPU: 4 cores
RAM: 8GB
Disk: 50GB SSD
OS: Linux (Ubuntu 20.04+)

# Recommended for production
CPU: 8 cores
RAM: 16GB
Disk: 100GB SSD + 500GB storage
OS: Ubuntu 22.04 LTS
```

### Software Dependencies

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose v2
sudo apt-get update
sudo apt-get install docker compose-plugin

# Verify installation
docker --version
docker compose version
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd dslToPngMCP
make setup-dev
```

### 2. Start Development Environment

```bash
make dev
```

### 3. Verify Deployment

```bash
make health
curl http://localhost/health
```

## 🛠️ Development Deployment

### Environment Setup

```bash
# 1. Create development environment
make setup-dev

# 2. Start all services
make dev

# 3. Check service status
make status

# 4. View logs
make dev-logs
```

### Development Configuration

The development environment uses:
- **Hot reloading**: Code changes reflect immediately
- **Debug mode**: Enhanced logging and error details
- **Self-signed SSL**: HTTPS available at `https://localhost`
- **Exposed ports**: Direct access to individual services

### Service Access Points

```bash
# Application endpoints
http://localhost          # Main application
https://localhost         # HTTPS (self-signed)
http://localhost/docs     # API documentation
http://localhost/health   # Health check

# Development debugging
http://localhost:6379     # Redis (direct access)
http://localhost:3001     # MCP Server (direct access)
http://localhost:9222     # Playwright DevTools
```

## 🏭 Production Deployment

### 1. Environment Preparation

```bash
# Copy production environment
cp .env.production .env

# Edit production configuration
nano .env
```

**Required Production Settings:**
```bash
DOMAIN_NAME=yourdomain.com              # Your actual domain
DSL_PNG_ENVIRONMENT=production          # Production mode
DSL_PNG_DEBUG=false                     # Disable debug
DSL_PNG_SECRET_KEY_FILE=/run/secrets/app_secret_key
```

### 2. Generate Production Secrets

```bash
# Create secrets directory
mkdir -p secrets
chmod 700 secrets

# Generate application secret key
openssl rand -base64 32 > secrets/app_secret_key.txt

# Generate Redis password
openssl rand -base64 16 > secrets/redis_password.txt

# Generate Grafana password (if monitoring enabled)
openssl rand -base64 16 > secrets/grafana_password.txt

# Secure secrets
chmod 600 secrets/*
```

### 3. SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)

```bash
# The deployment script will automatically request certificates
# Ensure DNS points to your server before deployment
nslookup yourdomain.com  # Should return your server IP
```

#### Option B: Custom Certificates

```bash
# Place your certificates in docker/nginx/ssl/
cp your-cert.pem docker/nginx/ssl/
cp your-key.pem docker/nginx/ssl/
```

### 4. Production Deployment

```bash
# Deploy with zero downtime
make deploy-prod

# Or force deployment (skip confirmations)
make deploy-prod-force
```

### 5. Post-Deployment Verification

```bash
# Run health checks
make health-prod

# Check service status
make status-prod

# Monitor logs
make prod-logs
```

## ⚙️ Configuration

### Environment Variables

#### Core Settings
```bash
# Application
DSL_PNG_ENVIRONMENT=production
DSL_PNG_DEBUG=false
DSL_PNG_LOG_LEVEL=INFO
DSL_PNG_WORKERS=4

# Domain and security
DOMAIN_NAME=yourdomain.com
DSL_PNG_ALLOWED_HOSTS=["yourdomain.com","api.yourdomain.com"]
DSL_PNG_CORS_ORIGINS=["https://yourdomain.com"]
```

#### Performance Tuning
```bash
# Worker configuration
DSL_PNG_WORKERS=4                    # FastAPI workers
CELERY_CONCURRENCY=4                 # Celery worker processes
DSL_PNG_BROWSER_POOL_SIZE=5          # Playwright browsers

# Rate limiting
DSL_PNG_RATE_LIMIT_REQUESTS=50       # Requests per minute
DSL_PNG_MAX_REQUEST_SIZE=50MB        # Max upload size

# Caching
DSL_PNG_CACHE_TTL=7200              # Cache TTL (seconds)
DSL_PNG_REDIS_MAX_CONNECTIONS=50     # Redis pool size
```

#### Resource Limits
```bash
# Memory limits (MB)
DSL_PNG_MEMORY_LIMIT_NGINX=128
DSL_PNG_MEMORY_LIMIT_REDIS=256
DSL_PNG_MEMORY_LIMIT_MCP=512
DSL_PNG_MEMORY_LIMIT_FASTAPI=512
DSL_PNG_MEMORY_LIMIT_CELERY=1024
DSL_PNG_MEMORY_LIMIT_BROWSER=2048

# CPU limits
DSL_PNG_CPU_LIMIT_NGINX=0.1
DSL_PNG_CPU_LIMIT_REDIS=0.2
DSL_PNG_CPU_LIMIT_MCP=0.5
DSL_PNG_CPU_LIMIT_FASTAPI=0.5
DSL_PNG_CPU_LIMIT_CELERY=1.0
DSL_PNG_CPU_LIMIT_BROWSER=2.0
```

### Docker Compose Overrides

Create `docker compose.override.yaml` for environment-specific customizations:

```yaml
# Example: Increase Celery workers for high load
services:
  celery-worker-5:
    extends:
      service: celery-worker-1
    container_name: dsl-celery-5-prod
    hostname: celery-worker-5
    environment:
      - WORKER_ID=5
```

## 📊 Scaling

### Horizontal Scaling

#### Scale FastAPI Servers
```bash
# Add more API server replicas
docker compose -f docker compose.prod.yaml up -d --scale fastapi-server=4
```

#### Scale Celery Workers
```bash
# Add more worker replicas
docker compose -f docker compose.prod.yaml up -d --scale celery-worker=8
```

### Vertical Scaling

#### Increase Resource Limits
```bash
# In .env file
DSL_PNG_MEMORY_LIMIT_CELERY=2048    # Increase memory
DSL_PNG_CPU_LIMIT_CELERY=2.0        # Increase CPU
```

#### Browser Pool Scaling
```bash
# Increase browser instances
DSL_PNG_BROWSER_POOL_SIZE=10
```

### Auto-Scaling (Advanced)

For Kubernetes deployment:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 📈 Monitoring

### Built-in Health Checks

```bash
# Comprehensive health check
make health

# Individual service health
curl https://yourdomain.com/health
```

### Metrics Collection

#### Prometheus + Grafana (Optional)
```bash
# Enable monitoring profile
docker compose -f docker compose.prod.yaml --profile monitoring up -d

# Access Grafana
https://yourdomain.com:3000
```

#### Application Metrics
```bash
# Prometheus metrics endpoint
curl https://yourdomain.com/metrics

# Nginx status
curl https://yourdomain.com/nginx-status
```

### Log Management

```bash
# View aggregated logs
make prod-logs

# Service-specific logs
docker compose -f docker compose.prod.yaml logs -f fastapi-server-1

# Log rotation configuration
# Logs are automatically rotated based on size and age
```

### Performance Monitoring

```bash
# Container resource usage
docker stats

# System resource monitoring
htop
iostat -x 1

# Network monitoring
netstat -tuln
ss -tuln
```

## 🔧 Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check Docker daemon
systemctl status docker

# Validate compose files
make validate

# Check resource availability
df -h
free -m
```

#### Memory Issues
```bash
# Check container memory usage
docker stats --no-stream

# Check system memory
free -m

# Adjust memory limits in .env
DSL_PNG_MEMORY_LIMIT_BROWSER=4096
```

#### Network Connectivity
```bash
# Test internal connectivity
docker exec nginx-proxy nc -zv fastapi-server-1 8000

# Check Docker networks
docker network ls
docker network inspect dsl-backend-prod
```

#### SSL Certificate Issues
```bash
# Check certificate status
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Renew Let's Encrypt certificate
docker exec nginx-proxy certbot renew
```

### Debug Mode

Enable debug mode for troubleshooting:
```bash
# In .env
DSL_PNG_DEBUG=true
DSL_PNG_LOG_LEVEL=DEBUG

# Restart services
make prod-restart
```

### Service Recovery

#### Restart Individual Services
```bash
docker compose -f docker compose.prod.yaml restart fastapi-server-1
```

#### Full System Recovery
```bash
# Stop all services
make prod-stop

# Clean up resources
make clean

# Restart
make prod
```

## 🔐 Security

### Security Checklist

- [ ] Strong passwords in `secrets/` directory
- [ ] HTTPS enabled with valid certificates
- [ ] Firewall configured (only ports 80, 443 open)
- [ ] Non-root containers
- [ ] Network isolation enabled
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers enabled
- [ ] Regular security updates

### Firewall Configuration

```bash
# Configure UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Container Security

```bash
# Security scan
make security-scan

# Check for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image dsl-png/fastapi-server:latest
```

### Secrets Management

```bash
# Rotate secrets
openssl rand -base64 32 > secrets/app_secret_key.txt
docker compose -f docker compose.prod.yaml up -d --force-recreate
```

## 💾 Backup & Recovery

### Automated Backups

```bash
# Enable backup in .env
DSL_PNG_BACKUP_ENABLED=true
DSL_PNG_BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

### Manual Backup

```bash
# Create backup
make backup

# Backup specific data
docker exec redis redis-cli BGSAVE
docker cp $(docker compose -f docker compose.prod.yaml ps -q redis):/data/redis/dump.rdb backup-$(date +%Y%m%d).rdb
```

### Recovery Procedures

#### Restore from Backup
```bash
# Stop services
make prod-stop

# Restore Redis data
docker cp backup-20240120.rdb $(docker compose -f docker compose.prod.yaml ps -q redis):/data/redis/dump.rdb

# Restart services
make prod
```

#### Disaster Recovery
```bash
# Full system restore
./scripts/disaster-recovery.sh --backup-date 2024-01-20
```

## 📚 Advanced Topics

### Custom Service Extensions

Create custom services by extending the base compose:
```yaml
# docker compose.custom.yaml
services:
  custom-service:
    image: custom/service:latest
    networks:
      - backend
    depends_on:
      - redis
```

### Performance Optimization

#### Database Tuning
```bash
# Redis optimization
# In docker/redis/redis-prod.conf
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

#### Nginx Optimization
```bash
# In docker/nginx/nginx.conf
worker_processes auto
worker_connections 2048
keepalive_timeout 30
```

### Integration with External Services

#### Load Balancer Integration
```yaml
# For AWS ALB, Azure LB, etc.
services:
  nginx-proxy:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dsl-png.rule=Host(`yourdomain.com`)"
```

#### CDN Integration
```bash
# Configure CDN for static assets
DSL_PNG_CDN_ENABLED=true
DSL_PNG_CDN_URL=https://cdn.yourdomain.com
```

## 🆘 Support

For additional support:
- Review logs: `make prod-logs`
- Run health checks: `make health-prod`
- Check documentation: `README.md`
- Open GitHub issue with logs and configuration