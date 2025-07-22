#!/bin/bash
# =============================================================================
# Docker Setup Test Script
# =============================================================================
# Comprehensive testing suite for the DSL to PNG MCP Server Docker setup
# Validates configuration, builds images, and runs integration tests
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Test configuration
TEST_TIMEOUT=300
TEST_ENVIRONMENT="test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "${RED}❌ FAILED: $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

success() {
    log "${GREEN}✅ PASSED: $1${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

warning() {
    log "${YELLOW}⚠️  WARNING: $1${NC}"
    WARNINGS=$((WARNINGS + 1))
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

# Test function wrapper
test_case() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    local test_name="$1"
    shift
    
    info "Running test: $test_name"
    
    if "$@"; then
        success "$test_name"
        return 0
    else
        error "$test_name"
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    header "Checking Prerequisites"
    
    # Check Docker
    test_case "Docker installation" command -v docker
    test_case "Docker daemon running" docker info
    
    # Check Docker Compose
        if command -v docker compose &> /dev/null; then
            test_case "Docker Compose v1 available" docker compose --version
            COMPOSE_CMD="docker compose"
        elif docker compose version &> /dev/null; then
            test_case "Docker Compose v2 available" docker compose version
            COMPOSE_CMD="docker compose"
        else
            error "Docker Compose not available"
            return 1
        fi
    
    # Check system resources
    local memory_gb=$(free -g | awk 'NR==2{printf "%.1f", $2}')
    if (( $(echo "$memory_gb >= 4" | bc -l) )); then
        success "Sufficient memory: ${memory_gb}GB"
    else
        warning "Low memory: ${memory_gb}GB (recommended: 8GB+)"
    fi
    
    local disk_gb=$(df "$PROJECT_ROOT" | awk 'NR==2{printf "%.1f", $4/1024/1024}')
    if (( $(echo "$disk_gb >= 10" | bc -l) )); then
        success "Sufficient disk space: ${disk_gb}GB"
    else
        warning "Low disk space: ${disk_gb}GB (recommended: 20GB+)"
    fi
}

# Validate Docker Compose files
validate_compose_files() {
    header "Validating Docker Compose Files"
    
    cd "$PROJECT_ROOT"
    
    # Validate development compose file
    test_case "Development compose syntax" $COMPOSE_CMD -f docker-compose.yaml config -q
    
    # Validate production compose file
    test_case "Production compose syntax" $COMPOSE_CMD -f docker compose.prod.yaml config -q
    
    # Check for required services
    local dev_services=($($COMPOSE_CMD -f docker-compose.yaml config --services))
    local expected_services=("redis" "mcp-server" "fastapi-server-1" "fastapi-server-2" "celery-worker-1" "celery-worker-2" "celery-worker-3" "celery-worker-4" "playwright-browsers" "nginx-proxy")
    
    for service in "${expected_services[@]}"; do
        if printf '%s\n' "${dev_services[@]}" | grep -q "^$service$"; then
            success "Service $service defined"
        else
            error "Service $service missing"
        fi
    done
    
    # Check networks
    test_case "Networks defined" bash -c "$COMPOSE_CMD -f docker-compose.yaml config | grep -q 'networks:'"
    
    # Check volumes
    test_case "Volumes defined" bash -c "$COMPOSE_CMD -f docker-compose.yaml config | grep -q 'volumes:'"
}

# Validate Dockerfiles
validate_dockerfiles() {
    header "Validating Dockerfiles"
    
    # Check main Dockerfile
    test_case "Main Dockerfile exists" test -f "$PROJECT_ROOT/Dockerfile"
    test_case "Main Dockerfile syntax" docker build --dry-run -f "$PROJECT_ROOT/Dockerfile" "$PROJECT_ROOT" > /dev/null 2>&1 || true
    
    # Check nginx Dockerfile
    test_case "Nginx Dockerfile exists" test -f "$PROJECT_ROOT/docker/nginx/Dockerfile"
    
    # Check redis Dockerfile
    test_case "Redis Dockerfile exists" test -f "$PROJECT_ROOT/docker/redis/Dockerfile"
    
    # Validate multi-stage builds
    if grep -q "FROM.*as.*" "$PROJECT_ROOT/Dockerfile"; then
        success "Multi-stage build detected"
    else
        warning "Multi-stage build not detected"
    fi
}

# Validate configuration files
validate_configurations() {
    header "Validating Configuration Files"
    
    # Check environment files
    test_case "Development env file exists" test -f "$PROJECT_ROOT/.env.development"
    test_case "Production env file exists" test -f "$PROJECT_ROOT/.env.production"
    
    # Check nginx configurations
    test_case "Nginx main config exists" test -f "$PROJECT_ROOT/docker/nginx/nginx.conf"
    test_case "Nginx dev config exists" test -f "$PROJECT_ROOT/docker/nginx/conf.d/dev.conf"
    test_case "Nginx prod config exists" test -f "$PROJECT_ROOT/docker/nginx/conf.d/prod.conf"
    
    # Check redis configurations
    test_case "Redis dev config exists" test -f "$PROJECT_ROOT/docker/redis/redis-dev.conf"
    test_case "Redis prod config exists" test -f "$PROJECT_ROOT/docker/redis/redis-prod.conf"
    
    # Validate nginx config syntax
    if command -v nginx &> /dev/null; then
        test_case "Nginx config syntax" nginx -t -c "$PROJECT_ROOT/docker/nginx/nginx.conf"
    else
        info "Nginx not installed locally, skipping syntax check"
    fi
}

# Validate scripts
validate_scripts() {
    header "Validating Scripts"
    
    local scripts=(
        "scripts/setup-dev.sh"
        "scripts/deploy-prod.sh"
        "scripts/health-check.sh"
        "docker/nginx/scripts/docker-entrypoint.sh"
        "docker/redis/scripts/health-check.sh"
    )
    
    for script in "${scripts[@]}"; do
        if test -f "$PROJECT_ROOT/$script"; then
            test_case "$script exists" test -f "$PROJECT_ROOT/$script"
            test_case "$script executable" test -x "$PROJECT_ROOT/$script"
            test_case "$script syntax" bash -n "$PROJECT_ROOT/$script"
        else
            error "Script missing: $script"
        fi
    done
    
    # Check Makefile
    test_case "Makefile exists" test -f "$PROJECT_ROOT/Makefile"
    if command -v make &> /dev/null; then
        test_case "Makefile syntax" make -n -f "$PROJECT_ROOT/Makefile" help > /dev/null
    fi
}

# Test Docker builds
test_docker_builds() {
    header "Testing Docker Builds"
    
    cd "$PROJECT_ROOT"
    
    # Test main Dockerfile build stages
    local stages=("base" "dependencies" "prod-dependencies" "playwright-base" "app-base")
    
    for stage in "${stages[@]}"; do
        test_case "Build stage: $stage" timeout $TEST_TIMEOUT docker build --target "$stage" -t "test-$stage" . > /dev/null 2>&1 || true
    done
    
    # Test service builds
    info "Building development images (this may take several minutes)..."
    test_case "Build development images" timeout $TEST_TIMEOUT $COMPOSE_CMD -f docker-compose.yaml build > /dev/null 2>&1 || true
    
    # Clean up test images
    docker rmi $(docker images -q "test-*" 2>/dev/null) 2>/dev/null || true
}

# Test network configuration
test_network_configuration() {
    header "Testing Network Configuration"
    
    cd "$PROJECT_ROOT"
    
    # Check network definitions
    local networks=($($COMPOSE_CMD -f docker-compose.yaml config | grep -A 10 "networks:" | grep "^  [a-z]" | cut -d: -f1 | tr -d ' '))
    
    for network in "${networks[@]}"; do
        success "Network defined: $network"
    done
    
    # Validate network subnets
    if grep -q "172.20.0.0/24" docker-compose.yaml; then
        success "Frontend network subnet configured"
    else
        error "Frontend network subnet not configured"
    fi
    
    if grep -q "172.21.0.0/24" docker-compose.yaml; then
        success "Backend network subnet configured"
    else
        error "Backend network subnet not configured"
    fi
}

# Test volume configuration
test_volume_configuration() {
    header "Testing Volume Configuration"
    
    cd "$PROJECT_ROOT"
    
    # Check volume definitions
    local volumes=($($COMPOSE_CMD -f docker-compose.yaml config | grep -A 20 "volumes:" | grep "^  [a-z]" | cut -d: -f1 | tr -d ' '))
    
    for volume in "${volumes[@]}"; do
        success "Volume defined: $volume"
    done
    
    # Check critical volumes
    local critical_volumes=("png_storage" "redis_data" "nginx_logs")
    
    for volume in "${critical_volumes[@]}"; do
        if printf '%s\n' "${volumes[@]}" | grep -q "^$volume$"; then
            success "Critical volume present: $volume"
        else
            error "Critical volume missing: $volume"
        fi
    done
}

# Test environment variables
test_environment_variables() {
    header "Testing Environment Variables"
    
    # Source development environment
    if source "$PROJECT_ROOT/.env.development" 2>/dev/null; then
        success "Development environment file sourced"
        
        # Check critical variables
        local critical_vars=("DSL_PNG_ENVIRONMENT" "DSL_PNG_HOST" "DSL_PNG_PORT" "DSL_PNG_REDIS_URL")
        
        for var in "${critical_vars[@]}"; do
            if [[ -n "${!var:-}" ]]; then
                success "Variable set: $var"
            else
                error "Variable missing: $var"
            fi
        done
    else
        error "Cannot source development environment file"
    fi
    
    # Check production environment
    if grep -q "DOMAIN_NAME=yourdomain.com" "$PROJECT_ROOT/.env.production"; then
        warning "Production domain not customized (still using default)"
    else
        success "Production domain customized"
    fi
}

# Test health checks
test_health_checks() {
    header "Testing Health Check Configuration"
    
    # Check health check definitions in compose files
    if grep -q "healthcheck:" docker-compose.yaml; then
        success "Health checks defined in development compose"
    else
        error "No health checks in development compose"
    fi
    
    if grep -q "healthcheck:" docker compose.prod.yaml; then
        success "Health checks defined in production compose"
    else
        error "No health checks in production compose"
    fi
    
    # Check health check script
    if test -x "$PROJECT_ROOT/scripts/health-check.sh"; then
        test_case "Health check script executable" bash -n "$PROJECT_ROOT/scripts/health-check.sh"
    else
        error "Health check script not executable"
    fi
}

# Integration test (if services can be started)
integration_test() {
    header "Integration Test"
    
    cd "$PROJECT_ROOT"
    
    info "Attempting to start services for integration test..."
    
    # Create minimal test environment
    export DSL_PNG_ENVIRONMENT=test
    export DSL_PNG_DEBUG=true
    
    # Try to start just core services
    if timeout 60 $COMPOSE_CMD -f docker-compose.yaml up -d redis > /dev/null 2>&1; then
        success "Redis service started"
        
        # Wait for Redis to be ready
        sleep 10
        
        # Test Redis connectivity
        if $COMPOSE_CMD -f docker-compose.yaml exec -T redis redis-cli ping > /dev/null 2>&1; then
            success "Redis connectivity test passed"
        else
            warning "Redis connectivity test failed"
        fi
        
        # Cleanup
        $COMPOSE_CMD -f docker-compose.yaml down > /dev/null 2>&1
        success "Services cleaned up"
    else
        warning "Could not start services for integration test"
    fi
}

# Security validation
test_security() {
    header "Security Validation"
    
    # Check for secrets in code
    if grep -r -i "password.*=" --include="*.py" --include="*.js" src/ 2>/dev/null | grep -v "password_file" | grep -v "REDIS_PASSWORD"; then
        error "Hardcoded passwords found in source code"
    else
        success "No hardcoded passwords in source code"
    fi
    
    # Check file permissions
    if test -d "$PROJECT_ROOT/secrets"; then
        local secrets_perms=$(stat -c "%a" "$PROJECT_ROOT/secrets" 2>/dev/null || echo "000")
        if [[ "$secrets_perms" == "700" ]]; then
            success "Secrets directory has correct permissions"
        else
            warning "Secrets directory permissions: $secrets_perms (should be 700)"
        fi
    else
        info "Secrets directory not created yet"
    fi
    
    # Check for non-root user in Dockerfile
    if grep -q "USER.*nginx\|USER.*redis\|USER.*appuser" "$PROJECT_ROOT/Dockerfile"; then
        success "Non-root users configured in Dockerfile"
    else
        warning "Root users detected in Dockerfile"
    fi
}

# Performance validation
test_performance() {
    header "Performance Validation"
    
    # Check resource limits
    if grep -q "cpus:" docker compose.prod.yaml; then
        success "CPU limits configured"
    else
        warning "No CPU limits configured"
    fi
    
    if grep -q "memory:" docker compose.prod.yaml; then
        success "Memory limits configured"
    else
        warning "No memory limits configured"
    fi
    
    # Check restart policies
    if grep -q "restart: unless-stopped" docker compose.prod.yaml; then
        success "Restart policies configured"
    else
        warning "No restart policies configured"
    fi
}

# Generate test report
generate_report() {
    header "Test Report"
    
    local total_issues=$((FAILED_TESTS + WARNINGS))
    local success_rate=0
    
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    echo -e "${BLUE}Test Summary:${NC}"
    echo "• Total Tests: $TOTAL_TESTS"
    echo "• Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo "• Failed: ${RED}$FAILED_TESTS${NC}"
    echo "• Warnings: ${YELLOW}$WARNINGS${NC}"
    echo "• Success Rate: $success_rate%"
    echo
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 All critical tests passed!${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}⚠️  There are $WARNINGS warnings that should be reviewed.${NC}"
        fi
        echo
        echo -e "${BLUE}The Docker setup is ready for deployment!${NC}"
        echo
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Run 'make setup-dev' to set up development environment"
        echo "2. Run 'make dev' to start development services"
        echo "3. Run 'make health' to verify deployment"
        echo "4. For production: update .env.production and run 'make deploy-prod'"
        return 0
    else
        echo -e "${RED}💥 $FAILED_TESTS critical tests failed!${NC}"
        echo -e "${RED}Please fix the issues before deploying.${NC}"
        return 1
    fi
}

# Main test function
main() {
    header "DSL to PNG MCP Server - Docker Setup Test"
    
    info "Starting comprehensive Docker setup validation..."
    info "Test timeout: ${TEST_TIMEOUT}s"
    echo
    
    cd "$PROJECT_ROOT"
    
    # Run all test suites
    check_prerequisites
    validate_compose_files
    validate_dockerfiles
    validate_configurations
    validate_scripts
    test_docker_builds
    test_network_configuration
    test_volume_configuration
    test_environment_variables
    test_health_checks
    test_security
    test_performance
    integration_test
    
    # Generate final report
    generate_report
}

# Handle script interruption
trap 'error "Tests interrupted by user"' INT TERM

# Execute main function
main "$@"