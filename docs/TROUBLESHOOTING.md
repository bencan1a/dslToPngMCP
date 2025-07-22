# Troubleshooting Guide

Comprehensive troubleshooting guide for the DSL to PNG MCP Server covering common issues, debugging procedures, and recovery techniques.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Performance Problems](#performance-problems)
- [Error Messages](#error-messages)
- [Log Analysis](#log-analysis)
- [Container Debugging](#container-debugging)
- [Recovery Procedures](#recovery-procedures)
- [Advanced Debugging](#advanced-debugging)

---

## Quick Diagnostics

### Health Check Commands

```bash
# Basic health check
curl http://localhost:8000/health

# Service-specific checks
docker compose ps                    # Container status
docker compose logs --tail=50      # Recent logs
redis-cli ping                      # Redis connectivity
```

### Essential Logs

```bash
# All services
docker compose logs -f

# Specific services
docker compose logs -f fastapi-server
docker compose logs -f celery-workers
docker compose logs -f mcp-server
docker compose logs -f redis
```

### System Resources

```bash
# Container resource usage
docker stats

# System resources
top
df -h        # Disk space
free -h      # Memory usage
```

---

## Common Issues

### 1. Service Won't Start

#### Symptoms
- Container exits immediately
- Health check fails
- Connection refused errors

#### Diagnosis
```bash
# Check container status
docker compose ps

# View startup logs
docker compose logs fastapi-server

# Check port conflicts
netstat -tulpn | grep :8000
lsof -i :8000
```

#### Solutions

**Port Already in Use**
```bash
# Find process using port
sudo lsof -i :8000
sudo kill -9 <PID>

# Use different port
export DSL_PNG_PORT=8080
docker compose up -d
```

**Permission Issues**
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER ./storage ./tmp
chmod -R 755 ./storage ./tmp
```

**Missing Environment Variables**
```bash
# Check environment file exists
ls -la .env

# Validate environment
docker compose config
```

### 2. Redis Connection Issues

#### Symptoms
- "Connection refused" to Redis
- Cache operations failing
- Celery workers not starting

#### Diagnosis
```bash
# Test Redis connectivity
redis-cli ping
redis-cli info

# Check Redis container
docker compose logs redis
docker compose exec redis redis-cli ping
```

#### Solutions

**Redis Container Not Running**
```bash
# Restart Redis
docker compose restart redis

# Check Redis logs
docker compose logs redis
```

**Redis Configuration Issues**
```bash
# Reset Redis data
docker compose down
docker volume rm dslToPngMCP_redis_data
docker compose up -d redis

# Check Redis configuration
docker compose exec redis cat /etc/redis/redis.conf
```

**Network Issues**
```bash
# Check Docker network
docker network ls
docker network inspect dslToPngMCP_default

# Recreate network
docker compose down
docker compose up -d
```

### 3. Browser Automation Failures

#### Symptoms
- "Browser not found" errors
- Playwright timeout errors
- Blank PNG outputs

#### Diagnosis
```bash
# Check browser container
docker compose logs playwright-browsers

# Test browser installation
docker compose exec playwright-browsers playwright --version

# Check available browsers
docker compose exec playwright-browsers ls -la /ms-playwright/
```

#### Solutions

**Browser Installation Issues**
```bash
# Reinstall browsers
docker compose exec playwright-browsers playwright install
docker compose exec playwright-browsers playwright install-deps

# Rebuild browser container
docker compose build playwright-browsers
```

**Insufficient Memory**
```bash
# Check system memory
free -h

# Increase shared memory
echo 'tmpfs /dev/shm tmpfs defaults,size=2G 0 0' >> /etc/fstab
mount -a

# Reduce browser pool size
export DSL_PNG_BROWSER_POOL_SIZE=2
```

**Display Issues**
```bash
# Check X11 display (if not headless)
echo $DISPLAY

# Force headless mode
export DSL_PNG_PLAYWRIGHT_HEADLESS=true

# Check browser dependencies
docker compose exec playwright-browsers ldd /ms-playwright/chromium-*/chrome
```

### 4. Rendering Failures

#### Symptoms
- Empty or corrupted PNG files
- Timeout errors
- CSS not applying correctly

#### Diagnosis
```bash
# Test simple DSL
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"dsl_content": "{\"width\": 100, \"height\": 100, \"elements\": []}"}'

# Check render logs
docker compose logs -f fastapi-server | grep "render"
```

#### Solutions

**DSL Syntax Errors**
```bash
# Validate DSL first
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @your-dsl.json

# Check validation response
jq '.errors' validation-response.json
```

**CSS Issues**
```json
{
  "elements": [{
    "type": "text",
    "text": "Test",
    "layout": {"x": 10, "y": 10, "width": 100, "height": 50},
    "style": {
      "fontSize": "16px",  // Use valid CSS values
      "color": "#000000"    // Use hex colors
    }
  }]
}
```

**Timeout Issues**
```bash
# Increase timeout
export DSL_PNG_RENDER_TIMEOUT=120

# Use async rendering for complex DSL
curl -X POST http://localhost:8000/render/async
```

### 5. High Memory Usage

#### Symptoms
- System running out of memory
- Containers being killed (OOMKilled)
- Slow performance

#### Diagnosis
```bash
# Monitor memory usage
docker stats
htop

# Check container memory limits
docker inspect <container_id> | grep -i memory

# Check system memory
cat /proc/meminfo
```

#### Solutions

**Optimize Browser Pool**
```bash
# Reduce browser instances
export DSL_PNG_BROWSER_POOL_SIZE=3

# Set memory limits
echo "
services:
  playwright-browsers:
    deploy:
      resources:
        limits:
          memory: 1G
" >> docker compose.override.yml
```

**Enable Swap**
```bash
# Create swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
```

**Clean Up Resources**
```bash
# Remove unused Docker resources
docker system prune -a

# Clear application cache
redis-cli FLUSHDB

# Restart services
docker compose restart
```

---

## Performance Problems

### 1. Slow Rendering

#### Symptoms
- Long response times (>30 seconds)
- High CPU usage
- Queue backlog

#### Diagnosis
```bash
# Check rendering time
time curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @test-dsl.json

# Monitor system resources
iostat 1
sar -u 1

# Check queue status
redis-cli LLEN celery
```

#### Solutions

**Optimize DSL**
```json
// Reduce element count
{
  "elements": [
    // Keep under 100 elements for best performance
  ]
}

// Use efficient layouts
{
  "type": "flex",
  "style": {"display": "flex", "gap": "16px"}
  // Instead of absolute positioning many elements
}

// Optimize images
{
  "type": "image",
  "src": "optimized-image.jpg",
  "style": {"width": "200px", "height": "150px"}
}
```

**Scale Workers**
```bash
# Increase Celery workers
export DSL_PNG_CELERY_WORKERS=8

# Scale FastAPI replicas
docker compose up -d --scale fastapi-server=4
```

**Use Async Rendering**
```bash
# For complex DSL documents
curl -X POST http://localhost:8000/render/async \
  -H "Content-Type: application/json" \
  -d @complex-dsl.json
```

### 2. Memory Leaks

#### Symptoms
- Memory usage continuously increasing
- System becomes unresponsive
- Out of memory errors

#### Diagnosis
```bash
# Monitor memory over time
while true; do
  echo "$(date): $(free -m | grep Mem | awk '{print $3}')"
  sleep 60
done > memory-usage.log

# Check for memory leaks in containers
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"
```

#### Solutions

**Restart Services Periodically**
```bash
# Restart every 24 hours (cron job)
0 2 * * * /usr/local/bin/docker compose -f /path/to/docker compose.yml restart

# Implement health-based restart
docker compose up -d --restart unless-stopped
```

**Memory Limits**
```yaml
# docker compose.yml
services:
  fastapi-server:
    deploy:
      resources:
        limits:
          memory: 2G
  
  celery-workers:
    deploy:
      resources:
        limits:
          memory: 1G
```

### 3. High CPU Usage

#### Symptoms
- System sluggish
- High load average
- Browser processes consuming CPU

#### Diagnosis
```bash
# Check CPU usage by process
top -p $(pgrep -d',' chrome)
htop

# Monitor load average
uptime
cat /proc/loadavg
```

#### Solutions

**Optimize Browser Settings**
```bash
# Reduce CPU usage
export DSL_PNG_PLAYWRIGHT_HEADLESS=true
export DSL_PNG_BROWSER_POOL_SIZE=4

# CPU limits for browsers
echo "
services:
  playwright-browsers:
    deploy:
      resources:
        limits:
          cpus: '2.0'
" >> docker compose.override.yml
```

**Process Scheduling**
```bash
# Lower priority for render processes
nice -n 10 docker compose up -d

# CPU affinity
taskset -c 0,1 docker compose up -d
```

---

## Error Messages

### HTTP Errors

#### 400 Bad Request

**Error Message:**
```json
{
  "error": "DSL parsing failed: Invalid JSON syntax at line 5",
  "error_code": "DSL_PARSE_ERROR"
}
```

**Solution:**
```bash
# Validate JSON syntax
jq . your-dsl.json

# Check for common issues
- Missing commas
- Unmatched brackets
- Invalid escape sequences
```

#### 422 Unprocessable Entity

**Error Message:**
```json
{
  "error": "Validation error: Element type 'invalid' not supported",
  "error_code": "DSL_VALIDATION_ERROR"
}
```

**Solution:**
```bash
# Check supported element types
curl http://localhost:8000/docs

# Use valid element types
["button", "text", "input", "image", "container", "grid", "flex", "card"]
```

#### 500 Internal Server Error

**Error Message:**
```json
{
  "error": "Internal server error",
  "error_code": "INTERNAL_ERROR"
}
```

**Solution:**
```bash
# Check server logs
docker compose logs fastapi-server

# Common causes:
- Database connection issues
- Browser automation failures
- Disk space problems
```

#### 503 Service Unavailable

**Error Message:**
```json
{
  "error": "Service temporarily unavailable",
  "error_code": "SERVICE_UNAVAILABLE"
}
```

**Solution:**
```bash
# Check service health
curl http://localhost:8000/health

# Restart unhealthy services
docker compose restart
```

### DSL Validation Errors

#### Invalid Element Structure

**Error:**
```
Element type 'input' cannot have children
```

**Solution:**
```json
// Wrong
{
  "type": "input",
  "children": [...]  // Inputs cannot have children
}

// Correct
{
  "type": "container",
  "children": [
    {"type": "input", "placeholder": "Username"}
  ]
}
```

#### Layout Errors

**Error:**
```
Layout coordinates outside canvas bounds
```

**Solution:**
```json
// Check element fits in canvas
{
  "width": 400,
  "height": 300,
  "elements": [{
    "layout": {
      "x": 100,     // x + width = 100 + 200 = 300 < 400 ✓
      "y": 50,      // y + height = 50 + 100 = 150 < 300 ✓
      "width": 200,
      "height": 100
    }
  }]
}
```

### Browser Errors

#### Browser Launch Failed

**Error:**
```
Failed to launch browser: No suitable browser found
```

**Solution:**
```bash
# Reinstall browsers
docker compose exec playwright-browsers playwright install

# Check browser permissions
docker compose exec playwright-browsers ls -la /ms-playwright/
```

#### Page Timeout

**Error:**
```
Page timeout after 30000ms
```

**Solution:**
```bash
# Increase timeout
export DSL_PNG_PLAYWRIGHT_TIMEOUT=60000

# Simplify DSL for faster rendering
# Remove complex animations or large images
```

---

## Log Analysis

### Log Locations

```bash
# Docker container logs
docker compose logs <service-name>

# Application logs (if volume mounted)
tail -f ./logs/application.log
tail -f ./logs/error.log

# System logs
journalctl -u docker
tail -f /var/log/syslog
```

### Log Levels and Meanings

| Level | Description | Action Required |
|-------|-------------|-----------------|
| `DEBUG` | Detailed execution info | None |
| `INFO` | General information | None |
| `WARNING` | Potential issues | Monitor |
| `ERROR` | Errors that don't stop service | Investigate |
| `CRITICAL` | Service-stopping errors | Immediate action |

### Common Log Patterns

#### Successful Render
```
INFO - Starting synchronous rendering task_id=sync
INFO - DSL parsing completed successfully parsing_time=0.023
INFO - HTML generation completed generation_time=0.145
INFO - PNG generation completed render_time=1.234
INFO - Synchronous render completed successfully file_size=45231
```

#### Failed Render
```
ERROR - DSL parsing failed: Invalid JSON syntax at line 5
ERROR - Validation errors: ['Element type button missing required label']
ERROR - Browser automation failed: Page timeout after 30000ms
ERROR - PNG generation failed: Insufficient memory
```

#### Performance Issues
```
WARNING - High memory usage: 85% of available memory
WARNING - Slow rendering detected: 45.2s for complex DSL
WARNING - Queue backlog detected: 25 pending tasks
WARNING - Browser pool exhausted: 0 available instances
```

### Log Analysis Commands

```bash
# Error frequency
grep "ERROR" logs/application.log | wc -l

# Performance analysis
grep "render_time" logs/application.log | awk '{print $NF}' | sort -n

# Memory usage patterns
grep "memory_usage" logs/application.log | tail -100

# Most common errors
grep "ERROR" logs/application.log | cut -d':' -f2 | sort | uniq -c | sort -nr
```

---

## Container Debugging

### Docker Debugging Commands

```bash
# Container inspection
docker inspect <container_name>

# Execute commands in container
docker compose exec fastapi-server bash
docker compose exec redis redis-cli

# Copy files from container
docker cp <container>:/app/logs/error.log ./error.log

# Monitor container resources
docker stats --no-stream
```

### Service-Specific Debugging

#### FastAPI Server
```bash
# Access application shell
docker compose exec fastapi-server python

# Check dependencies
docker compose exec fastapi-server pip list

# Test internal endpoints
docker compose exec fastapi-server curl localhost:8000/health
```

#### Celery Workers
```bash
# Check worker status
docker compose exec celery-workers celery -A src.core.queue.tasks inspect active

# Monitor task execution
docker compose exec celery-workers celery -A src.core.queue.tasks events

# Purge task queue
docker compose exec celery-workers celery -A src.core.queue.tasks purge
```

#### Redis
```bash
# Check Redis stats
docker compose exec redis redis-cli info

# Monitor Redis commands
docker compose exec redis redis-cli monitor

# Check memory usage
docker compose exec redis redis-cli info memory
```

#### Browser Container
```bash
# Test browser installation
docker compose exec playwright-browsers playwright --version

# Check available browsers
docker compose exec playwright-browsers ls -la /ms-playwright/

# Test browser launch
docker compose exec playwright-browsers python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    print('Browser launched successfully')
    browser.close()
"
```

### Network Debugging

```bash
# Check container networking
docker network ls
docker network inspect dslToPngMCP_default

# Test connectivity between containers
docker compose exec fastapi-server ping redis
docker compose exec fastapi-server nslookup redis

# Check exposed ports
docker compose port fastapi-server 8000
netstat -tulpn | grep :8000
```

---

## Recovery Procedures

### 1. Complete System Recovery

```bash
# Emergency restart
docker compose down
docker compose up -d

# Full reset (WARNING: loses data)
docker compose down -v
docker system prune -a
docker compose up -d
```

### 2. Service-Specific Recovery

#### Redis Data Corruption
```bash
# Stop Redis
docker compose stop redis

# Backup corrupted data
docker run --rm -v dslToPngMCP_redis_data:/data -v $(pwd):/backup busybox cp -r /data /backup/redis-backup

# Reset Redis
docker volume rm dslToPngMCP_redis_data
docker compose up -d redis
```

#### Browser Pool Recovery
```bash
# Kill all browser processes
docker compose exec playwright-browsers pkill -f chrome

# Restart browser container
docker compose restart playwright-browsers

# Reinstall browsers if needed
docker compose exec playwright-browsers playwright install --force
```

#### Storage Recovery
```bash
# Check disk space
df -h

# Clean up temporary files
docker compose exec fastapi-server find /app/tmp -type f -mtime +1 -delete

# Clean up old renders
docker compose exec fastapi-server find /app/storage -name "*.png" -mtime +7 -delete
```

### 3. Configuration Recovery

#### Reset Environment Configuration
```bash
# Backup current config
cp .env .env.backup

# Reset to defaults
cp .env.example .env

# Restore custom settings
nano .env
```

#### Reset Docker Configuration
```bash
# Recreate containers
docker compose down
docker compose rm -f
docker compose up -d --force-recreate
```

### 4. Data Recovery

#### Backup and Restore
```bash
# Create backup
docker run --rm -v dslToPngMCP_redis_data:/data -v $(pwd):/backup busybox tar czf /backup/redis-backup.tar.gz /data

# Restore backup
docker volume create dslToPngMCP_redis_data
docker run --rm -v dslToPngMCP_redis_data:/data -v $(pwd):/backup busybox tar xzf /backup/redis-backup.tar.gz -C /
```

---

## Advanced Debugging

### 1. Performance Profiling

#### CPU Profiling
```bash
# Install profiling tools
docker compose exec fastapi-server pip install py-spy

# Profile Python application
docker compose exec fastapi-server py-spy top --pid 1

# Generate flame graph
docker compose exec fastapi-server py-spy record -o profile.svg --pid 1 --duration 60
```

#### Memory Profiling
```bash
# Install memory profiler
docker compose exec fastapi-server pip install memory-profiler

# Profile memory usage
docker compose exec fastapi-server python -m memory_profiler src/api/main.py
```

### 2. Network Analysis

```bash
# Install network tools
docker compose exec fastapi-server apt update && apt install -y tcpdump

# Capture network traffic
docker compose exec fastapi-server tcpdump -i eth0 -w /tmp/network.pcap

# Analyze with tshark
docker compose exec fastapi-server tshark -r /tmp/network.pcap
```

### 3. Database Analysis

```bash
# Redis slow query log
docker compose exec redis redis-cli config set slowlog-log-slower-than 1000
docker compose exec redis redis-cli slowlog get 10

# Redis memory analysis
docker compose exec redis redis-cli --bigkeys
```

### 4. Custom Debugging Scripts

#### Health Check Script
```bash
#!/bin/bash
# health-check.sh

echo "=== DSL to PNG Health Check ==="

# Check services
services=("fastapi-server" "celery-workers" "redis" "playwright-browsers")
for service in "${services[@]}"; do
    if docker compose ps -q "$service" > /dev/null; then
        echo "✓ $service: Running"
    else
        echo "✗ $service: Not running"
    fi
done

# Check API
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ API: Responding"
else
    echo "✗ API: Not responding"
fi

# Check Redis
if docker compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis: Connected"
else
    echo "✗ Redis: Connection failed"
fi
```

#### Performance Monitor
```bash
#!/bin/bash
# monitor.sh

while true; do
    echo "$(date): $(docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}')"
    sleep 30
done > performance.log
```

---

## Getting Additional Help

### 1. Enable Debug Logging

```bash
# Increase log verbosity
export DSL_PNG_LOG_LEVEL=DEBUG
docker compose restart
```

### 2. Collect Diagnostic Information

```bash
# System info
uname -a
docker version
docker compose version

# Service status
docker compose ps
docker compose logs --tail=100

# Resource usage
docker stats --no-stream
free -h
df -h
```

### 3. Create Support Bundle

```bash
#!/bin/bash
# collect-support-info.sh

BUNDLE_DIR="support-$(date +%Y%m%d-%H%M%S)"
mkdir "$BUNDLE_DIR"

# System information
uname -a > "$BUNDLE_DIR/system-info.txt"
docker version > "$BUNDLE_DIR/docker-version.txt"
docker compose version > "$BUNDLE_DIR/compose-version.txt"

# Service status
docker compose ps > "$BUNDLE_DIR/service-status.txt"
docker compose config > "$BUNDLE_DIR/compose-config.yml"

# Logs
docker compose logs --tail=1000 > "$BUNDLE_DIR/service-logs.txt"

# Resource usage
docker stats --no-stream > "$BUNDLE_DIR/resource-usage.txt"
free -h > "$BUNDLE_DIR/memory-usage.txt"
df -h > "$BUNDLE_DIR/disk-usage.txt"

# Configuration (remove sensitive data)
cp .env "$BUNDLE_DIR/env-config.txt"
sed -i 's/SECRET_KEY=.*/SECRET_KEY=<redacted>/' "$BUNDLE_DIR/env-config.txt"
sed -i 's/API_KEY=.*/API_KEY=<redacted>/' "$BUNDLE_DIR/env-config.txt"

# Create archive
tar czf "$BUNDLE_DIR.tar.gz" "$BUNDLE_DIR"
rm -rf "$BUNDLE_DIR"

echo "Support bundle created: $BUNDLE_DIR.tar.gz"
```

For additional support:
- Check the [API Documentation](./API.md) for usage examples
- Review the [User Guide](./USER_GUIDE.md) for common patterns
- See the [Operations Guide](./OPERATIONS.md) for production issues
- Report bugs on the project repository issue tracker