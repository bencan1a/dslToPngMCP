#!/bin/bash
# =============================================================================
# Health Check Script
# =============================================================================
# Comprehensive health check for all DSL to PNG MCP Server services
# Validates connectivity, performance, and functionality across the entire system
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Health check configuration
TIMEOUT=30
ENVIRONMENT="development"  # Default to development
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "${RED}❌ ERROR: $1${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

success() {
    log "${GREEN}✅ SUCCESS: $1${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

warning() {
    log "${YELLOW}⚠️  WARNING: $1${NC}"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
}

info() {
    log "${BLUE}ℹ️  INFO: $1${NC}"
}

header() {
    echo
    echo -e "${PURPLE}===============================================================================${NC}"
    echo -e "${PURPLE} $1${NC}"
    echo -e "${PURPLE}===============================================================================${NC}"
    echo
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --production)
                ENVIRONMENT="production"
                COMPOSE_FILE="$PROJECT_ROOT/docker compose.prod.yaml"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Show help
show_help() {
    cat << EOF
Health Check Script for DSL to PNG MCP Server

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --environment ENV      Environment to check (development|production)
    --production          Use production environment
    --timeout SECONDS     Timeout for individual checks (default: 30)
    --help               Show this help message

EXAMPLES:
    $0                           # Check development environment
    $0 --production             # Check production environment
    $0 --timeout 60             # Use 60 second timeout
EOF
}

# Increment total checks counter
check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

# Check if Docker is running
check_docker() {
    header "Docker System Check"
    
    check
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            success "Docker daemon is running"
            info "Docker version: $(docker --version)"
        else
            error "Docker daemon is not running"
            return 1
        fi
    else
        error "Docker is not installed"
        return 1
    fi
    
    check
    if command -v docker compose &> /dev/null; then
        success "Docker Compose is available"
        info "Docker Compose version: $(docker compose --version)"
    elif docker compose version &> /dev/null; then
        success "Docker Compose (v2) is available"
        info "Docker Compose version: $(docker compose version)"
    else
        error "Docker Compose is not available"
        return 1
    fi
}

# Check container status
check_containers() {
    header "Container Status Check"
    
    cd "$PROJECT_ROOT"
    
    # Get list of expected services
    local services
    if command -v docker compose &> /dev/null; then
        services=($(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null))
    else
        services=($(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null))
    fi
    
    if [[ ${#services[@]} -eq 0 ]]; then
        error "No services found in compose file"
        return 1
    fi
    
    for service in "${services[@]}"; do
        check
        if command -v docker compose &> /dev/null; then
            local status=$(docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | tail -n +3 | awk '{print $4}' | head -1)
        else
            local status=$(docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | tail -n +2 | awk '{print $3}' | head -1)
        fi
        
        case "$status" in
            "Up"|"running")
                success "Service $service is running"
                ;;
            "Exit")
                error "Service $service has exited"
                ;;
            "")
                error "Service $service is not found"
                ;;
            *)
                warning "Service $service status: $status"
                ;;
        esac
    done
}

# Check service health
check_service_health() {
    header "Service Health Check"
    
    # Define service health check endpoints
    local health_checks=(
        "nginx-proxy:80:/health"
        "fastapi-server-1:8000:/health"
        "fastapi-server-2:8000:/health"
    )
    
    for health_check in "${health_checks[@]}"; do
        check
        IFS=':' read -ra parts <<< "$health_check"
        local service="${parts[0]}"
        local port="${parts[1]}"
        local endpoint="${parts[2]}"
        
        # Get container name/IP
        local container_name
        if command -v docker compose &> /dev/null; then
            container_name=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null)
        else
            container_name=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null)
        fi
        
        if [[ -n "$container_name" ]]; then
            local container_ip=$(docker inspect "$container_name" --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null | head -1)
            
            if [[ -n "$container_ip" ]]; then
                if timeout "$TIMEOUT" curl -sf "http://$container_ip:$port$endpoint" &> /dev/null; then
                    success "Health check passed for $service"
                else
                    error "Health check failed for $service"
                fi
            else
                warning "Could not get IP for $service"
            fi
        else
            warning "Service $service not found for health check"
        fi
    done
}

# Check Redis connectivity
check_redis() {
    header "Redis Connectivity Check"
    
    check
    local redis_container
    if command -v docker compose &> /dev/null; then
        redis_container=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null)
    else
        redis_container=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null)
    fi
    
    if [[ -n "$redis_container" ]]; then
        if docker exec "$redis_container" redis-cli ping &> /dev/null; then
            success "Redis is responding to ping"
        else
            error "Redis is not responding"
            return 1
        fi
        
        # Check Redis memory usage
        check
        local memory_info=$(docker exec "$redis_container" redis-cli info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        if [[ -n "$memory_info" ]]; then
            success "Redis memory usage: $memory_info"
        else
            warning "Could not get Redis memory info"
        fi
        
        # Test basic Redis functionality
        check
        local test_key="health_check_$(date +%s)"
        if docker exec "$redis_container" redis-cli set "$test_key" "test" EX 60 &> /dev/null && \
           docker exec "$redis_container" redis-cli get "$test_key" &> /dev/null; then
            success "Redis SET/GET operations working"
            docker exec "$redis_container" redis-cli del "$test_key" &> /dev/null
        else
            error "Redis SET/GET operations failed"
        fi
    else
        error "Redis container not found"
    fi
}

# Check API endpoints
check_api_endpoints() {
    header "API Endpoints Check"
    
    # Determine the base URL
    local base_url
    if [[ "$ENVIRONMENT" == "production" ]]; then
        local domain=$(grep DOMAIN_NAME "$PROJECT_ROOT/.env.production" 2>/dev/null | cut -d'=' -f2 || echo "localhost")
        base_url="https://$domain"
    else
        base_url="http://localhost"
    fi
    
    local endpoints=(
        "/health"
        "/docs"
        "/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        check
        local url="$base_url$endpoint"
        
        if timeout "$TIMEOUT" curl -sf "$url" &> /dev/null; then
            success "Endpoint $endpoint is accessible"
        else
            error "Endpoint $endpoint is not accessible"
        fi
    done
}

# Check file system and volumes
check_filesystem() {
    header "File System Check"
    
    # Check required directories
    local required_dirs=(
        "$PROJECT_ROOT/data/redis"
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/secrets"
    )
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        required_dirs+=(
            "/opt/dsl-png/storage/png"
            "/opt/dsl-png/logs"
        )
    else
        required_dirs+=(
            "$PROJECT_ROOT/data/storage/png"
        )
    fi
    
    for dir in "${required_dirs[@]}"; do
        check
        if [[ -d "$dir" ]]; then
            success "Directory exists: $dir"
            
            # Check permissions
            if [[ -w "$dir" ]]; then
                success "Directory is writable: $dir"
            else
                warning "Directory is not writable: $dir"
            fi
        else
            error "Directory missing: $dir"
        fi
    done
    
    # Check disk space
    check
    local available_space
    if [[ "$ENVIRONMENT" == "production" ]]; then
        available_space=$(df /opt/dsl-png 2>/dev/null | awk 'NR==2 {print $4}' || echo "0")
    else
        available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    fi
    
    local available_gb=$((available_space / 1024 / 1024))
    if [[ $available_gb -gt 5 ]]; then
        success "Sufficient disk space: ${available_gb}GB available"
    elif [[ $available_gb -gt 1 ]]; then
        warning "Low disk space: ${available_gb}GB available"
    else
        error "Critical disk space: ${available_gb}GB available"
    fi
}

# Check network connectivity
check_network() {
    header "Network Connectivity Check"
    
    # Check Docker networks
    local networks
    if command -v docker compose &> /dev/null; then
        networks=($(docker compose -f "$COMPOSE_FILE" config | grep -A 10 "networks:" | grep "^  [a-z]" | cut -d: -f1 | tr -d ' '))
    else
        networks=($(docker compose -f "$COMPOSE_FILE" config | grep -A 10 "networks:" | grep "^  [a-z]" | cut -d: -f1 | tr -d ' '))
    fi
    
    for network in "${networks[@]}"; do
        check
        if docker network ls | grep -q "$network"; then
            success "Docker network exists: $network"
        else
            error "Docker network missing: $network"
        fi
    done
    
    # Check service-to-service connectivity
    check
    local nginx_container
    if command -v docker compose &> /dev/null; then
        nginx_container=$(docker compose -f "$COMPOSE_FILE" ps -q nginx-proxy 2>/dev/null)
    else
        nginx_container=$(docker compose -f "$COMPOSE_FILE" ps -q nginx-proxy 2>/dev/null)
    fi
    
    if [[ -n "$nginx_container" ]]; then
        if docker exec "$nginx_container" nc -z fastapi-server-1 8000 &> /dev/null; then
            success "Nginx can reach FastAPI server 1"
        else
            error "Nginx cannot reach FastAPI server 1"
        fi
    else
        warning "Nginx container not found for connectivity test"
    fi
}

# Check resource usage
check_resources() {
    header "Resource Usage Check"
    
    # Check container resource usage
    check
    local containers
    if command -v docker compose &> /dev/null; then
        containers=($(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null))
    else
        containers=($(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null))
    fi
    
    if [[ ${#containers[@]} -gt 0 ]]; then
        local stats=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" "${containers[@]}" 2>/dev/null)
        
        if [[ -n "$stats" ]]; then
            success "Container resource usage:"
            echo "$stats" | head -1  # Header
            echo "$stats" | tail -n +2 | while read -r line; do
                info "$line"
            done
        else
            warning "Could not get container resource usage"
        fi
    else
        error "No containers found for resource check"
    fi
    
    # Check system resources
    check
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "unknown")
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' 2>/dev/null || echo "unknown")
    
    if [[ "$cpu_usage" != "unknown" ]] && [[ "$memory_usage" != "unknown" ]]; then
        success "System resources: CPU ${cpu_usage}%, Memory ${memory_usage}%"
    else
        warning "Could not get system resource usage"
    fi
}

# Generate health report
generate_report() {
    header "Health Check Summary"
    
    local total_score=0
    local max_score=$TOTAL_CHECKS
    
    if [[ $max_score -gt 0 ]]; then
        total_score=$PASSED_CHECKS
        local success_rate=$((total_score * 100 / max_score))
        
        echo -e "${BLUE}Health Check Results:${NC}"
        echo "• Total Checks: $TOTAL_CHECKS"
        echo "• Passed: ${GREEN}$PASSED_CHECKS${NC}"
        echo "• Failed: ${RED}$FAILED_CHECKS${NC}"
        echo "• Warnings: ${YELLOW}$WARNING_CHECKS${NC}"
        echo "• Success Rate: $success_rate%"
        echo
        
        if [[ $FAILED_CHECKS -eq 0 ]]; then
            echo -e "${GREEN}🎉 All critical health checks passed!${NC}"
            if [[ $WARNING_CHECKS -gt 0 ]]; then
                echo -e "${YELLOW}⚠️  There are $WARNING_CHECKS warnings that should be reviewed.${NC}"
            fi
            return 0
        else
            echo -e "${RED}💥 $FAILED_CHECKS critical health checks failed!${NC}"
            echo -e "${RED}The system is not healthy and requires immediate attention.${NC}"
            return 1
        fi
    else
        error "No health checks were performed"
        return 1
    fi
}

# Main health check function
main() {
    header "DSL to PNG MCP Server - Health Check"
    
    info "Environment: $ENVIRONMENT"
    info "Compose file: $COMPOSE_FILE"
    info "Timeout: ${TIMEOUT}s"
    echo
    
    # Parse arguments
    parse_arguments "$@"
    
    cd "$PROJECT_ROOT"
    
    # Perform all health checks
    check_docker
    check_containers
    check_service_health
    check_redis
    check_api_endpoints
    check_filesystem
    check_network
    check_resources
    
    # Generate final report
    generate_report
}

# Execute main function
main "$@"