#!/bin/bash
# =============================================================================
# Redis Health Check Script
# =============================================================================
# Comprehensive health check for Redis service including connectivity,
# memory usage, and basic functionality tests
# =============================================================================

set -euo pipefail

# Configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
TIMEOUT=5
MAX_MEMORY_PERCENT=90

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Error function
error() {
    log "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Success function
success() {
    log "${GREEN}SUCCESS: $1${NC}"
}

# Warning function
warning() {
    log "${YELLOW}WARNING: $1${NC}"
}

# Check Redis connectivity
check_connectivity() {
    log "Checking Redis connectivity..."
    
    if [ -n "$REDIS_PASSWORD" ]; then
        if ! timeout $TIMEOUT redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
            error "Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
        fi
    else
        if ! timeout $TIMEOUT redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
            error "Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
        fi
    fi
    
    success "Redis connectivity OK"
}

# Check Redis memory usage
check_memory() {
    log "Checking Redis memory usage..."
    
    local cmd_prefix=""
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    # Get memory info
    local used_memory
    local max_memory
    
    used_memory=$($cmd_prefix info memory | grep "used_memory:" | cut -d: -f2 | tr -d '\r')
    max_memory=$($cmd_prefix config get maxmemory | tail -1 | tr -d '\r')
    
    if [ "$max_memory" != "0" ]; then
        local memory_percent=$((used_memory * 100 / max_memory))
        
        if [ $memory_percent -gt $MAX_MEMORY_PERCENT ]; then
            warning "Memory usage is high: ${memory_percent}%"
        else
            success "Memory usage OK: ${memory_percent}%"
        fi
    else
        success "No memory limit configured"
    fi
}

# Check Redis functionality
check_functionality() {
    log "Checking Redis functionality..."
    
    local cmd_prefix=""
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    # Test basic SET/GET operations
    local test_key="health_check_$(date +%s)"
    local test_value="health_check_value"
    
    # Set test key
    if ! $cmd_prefix set "$test_key" "$test_value" EX 60 > /dev/null 2>&1; then
        error "Cannot SET test key"
    fi
    
    # Get test key
    local retrieved_value
    retrieved_value=$($cmd_prefix get "$test_key" 2>/dev/null | tr -d '\r')
    
    if [ "$retrieved_value" != "$test_value" ]; then
        error "Cannot GET test key or value mismatch"
    fi
    
    # Clean up test key
    $cmd_prefix del "$test_key" > /dev/null 2>&1
    
    success "Redis functionality OK"
}

# Check Redis persistence
check_persistence() {
    log "Checking Redis persistence..."
    
    local cmd_prefix=""
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    # Check last save time
    local last_save
    last_save=$($cmd_prefix lastsave 2>/dev/null | tr -d '\r')
    
    if [ -n "$last_save" ] && [ "$last_save" != "0" ]; then
        success "Redis persistence OK (last save: $last_save)"
    else
        warning "No recent persistence activity detected"
    fi
}

# Check Redis replication (if applicable)
check_replication() {
    log "Checking Redis replication status..."
    
    local cmd_prefix=""
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        cmd_prefix="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    local role
    role=$($cmd_prefix info replication | grep "role:" | cut -d: -f2 | tr -d '\r')
    
    case "$role" in
        "master")
            local connected_slaves
            connected_slaves=$($cmd_prefix info replication | grep "connected_slaves:" | cut -d: -f2 | tr -d '\r')
            success "Redis role: master with $connected_slaves connected slaves"
            ;;
        "slave")
            local master_link_status
            master_link_status=$($cmd_prefix info replication | grep "master_link_status:" | cut -d: -f2 | tr -d '\r')
            if [ "$master_link_status" = "up" ]; then
                success "Redis role: slave with master link up"
            else
                warning "Redis role: slave with master link down"
            fi
            ;;
        *)
            success "Redis role: $role"
            ;;
    esac
}

# Main health check function
main() {
    log "Starting Redis health check..."
    
    # Read password from file if available
    if [ -f "/run/secrets/redis_password" ]; then
        REDIS_PASSWORD=$(cat /run/secrets/redis_password)
    fi
    
    # Run all checks
    check_connectivity
    check_memory
    check_functionality
    check_persistence
    check_replication
    
    success "All Redis health checks passed!"
    exit 0
}

# Execute main function
main "$@"