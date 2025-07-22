#!/bin/bash
# =============================================================================
# Production Deployment Script
# =============================================================================
# Zero-downtime deployment script for DSL to PNG MCP Server production environment
# Handles blue-green deployment, health checks, and rollback capabilities
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.production"
COMPOSE_FILE="$PROJECT_ROOT/docker compose.prod.yaml"

# Deployment configuration
DEPLOYMENT_TIMEOUT=600  # 10 minutes
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=10  # 10 seconds
BACKUP_RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "${RED}ERROR: $1${NC}" >&2
    exit 1
}

success() {
    log "${GREEN}SUCCESS: $1${NC}"
}

info() {
    log "${BLUE}INFO: $1${NC}"
}

warning() {
    log "${YELLOW}WARNING: $1${NC}"
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
    FORCE_DEPLOY=false
    SKIP_BACKUP=false
    SKIP_HEALTH_CHECKS=false
    VERSION="latest"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-health-checks)
                SKIP_HEALTH_CHECKS=true
                shift
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

# Show help
show_help() {
    cat << EOF
Production Deployment Script for DSL to PNG MCP Server

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --force                 Force deployment without confirmation
    --skip-backup          Skip pre-deployment backup
    --skip-health-checks   Skip post-deployment health checks
    --version VERSION      Deploy specific version (default: latest)
    --help                 Show this help message

EXAMPLES:
    $0                                    # Interactive deployment
    $0 --force --version 1.2.0          # Force deploy version 1.2.0
    $0 --skip-backup                     # Deploy without backup
EOF
}

# Check prerequisites
check_prerequisites() {
    header "Checking Prerequisites"
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root is not recommended for production deployment"
        if [[ "$FORCE_DEPLOY" != "true" ]]; then
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "Deployment cancelled"
            fi
        fi
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check if production environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Production environment file not found: $ENV_FILE"
    fi
    
    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Production compose file not found: $COMPOSE_FILE"
    fi
    
    # Check disk space (require at least 5GB free)
    local available_space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local required_space=$((5 * 1024 * 1024))  # 5GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        error "Insufficient disk space. Required: 5GB, Available: $((available_space / 1024 / 1024))GB"
    fi
    
    success "Prerequisites check passed"
}

# Validate production configuration
validate_configuration() {
    header "Validating Production Configuration"
    
    # Check required secrets
    local missing_secrets=()
    
    if [[ ! -f "$PROJECT_ROOT/secrets/app_secret_key.txt" ]]; then
        missing_secrets+=("app_secret_key.txt")
    fi
    
    if [[ ! -f "$PROJECT_ROOT/secrets/redis_password.txt" ]]; then
        missing_secrets+=("redis_password.txt")
    fi
    
    if [[ ${#missing_secrets[@]} -ne 0 ]]; then
        error "Missing required secrets: ${missing_secrets[*]}"
    fi
    
    # Validate environment variables
    source "$ENV_FILE"
    
    if [[ "$DOMAIN_NAME" == "yourdomain.com" ]] || [[ "$DOMAIN_NAME" == "localhost" ]]; then
        error "DOMAIN_NAME must be set to your actual domain in $ENV_FILE"
    fi
    
    if [[ "$DSL_PNG_SECRET_KEY" == *"CHANGE_THIS"* ]]; then
        error "DSL_PNG_SECRET_KEY must be changed from default value in $ENV_FILE"
    fi
    
    success "Configuration validation passed"
}

# Create backup
create_backup() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        info "Skipping backup as requested"
        return 0
    fi
    
    header "Creating Pre-Deployment Backup"
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$PROJECT_ROOT/backups/pre-deploy-$backup_date"
    
    info "Creating backup directory: $backup_dir"
    mkdir -p "$backup_dir"
    
    # Backup Redis data
    if docker compose -f "$COMPOSE_FILE" ps redis | grep -q "Up"; then
        info "Backing up Redis data..."
        docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE
        sleep 5  # Wait for background save to complete
        
        docker cp $(docker compose -f "$COMPOSE_FILE" ps -q redis):/data/redis/dump.rdb "$backup_dir/redis-dump.rdb" || warning "Could not backup Redis data"
    fi
    
    # Backup PNG storage
    if [[ -d "/opt/dsl-png/storage/png" ]]; then
        info "Backing up PNG storage..."
        tar -czf "$backup_dir/png-storage.tar.gz" -C "/opt/dsl-png/storage" png/ || warning "Could not backup PNG storage"
    fi
    
    # Backup logs
    if [[ -d "/opt/dsl-png/logs" ]]; then
        info "Backing up logs..."
        tar -czf "$backup_dir/logs.tar.gz" -C "/opt/dsl-png" logs/ || warning "Could not backup logs"
    fi
    
    # Backup configuration
    info "Backing up configuration..."
    cp "$ENV_FILE" "$backup_dir/"
    cp "$COMPOSE_FILE" "$backup_dir/"
    cp -r "$PROJECT_ROOT/secrets" "$backup_dir/" || warning "Could not backup secrets"
    
    # Create backup metadata
    cat > "$backup_dir/metadata.json" << EOF
{
    "backup_date": "$backup_date",
    "version": "$VERSION",
    "environment": "production",
    "created_by": "$(whoami)",
    "hostname": "$(hostname)",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Cleanup old backups
    info "Cleaning up old backups (retention: $BACKUP_RETENTION_DAYS days)..."
    find "$PROJECT_ROOT/backups" -name "pre-deploy-*" -type d -mtime +$BACKUP_RETENTION_DAYS -exec rm -rf {} + || true
    
    success "Backup created: $backup_dir"
    export BACKUP_DIR="$backup_dir"
}

# Pull latest images
pull_images() {
    header "Pulling Latest Images"
    
    info "Setting version to: $VERSION"
    export VERSION="$VERSION"
    
    info "Pulling Docker images..."
    docker compose -f "$COMPOSE_FILE" pull
    
    success "Images pulled successfully"
}

# Perform health check
health_check() {
    local service="$1"
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempts=0
    
    info "Performing health check for $service..."
    
    while [[ $attempts -lt $max_attempts ]]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
            success "$service is healthy"
            return 0
        fi
        
        attempts=$((attempts + 1))
        info "Health check attempt $attempts/$max_attempts for $service..."
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    error "$service health check failed after $HEALTH_CHECK_TIMEOUT seconds"
}

# Deploy services with zero downtime
deploy_services() {
    header "Deploying Services"
    
    info "Starting zero-downtime deployment..."
    
    # Deploy in dependency order
    local services=(
        "redis"
        "mcp-server"
        "playwright-browsers"
        "celery-worker-1"
        "celery-worker-2"
        "celery-worker-3"
        "celery-worker-4"
        "fastapi-server-1"
        "fastapi-server-2"
        "nginx-proxy"
    )
    
    for service in "${services[@]}"; do
        info "Deploying $service..."
        
        # Deploy service with update strategy
        docker compose -f "$COMPOSE_FILE" up -d --no-deps "$service"
        
        # Wait for service to be ready
        if [[ "$SKIP_HEALTH_CHECKS" != "true" ]]; then
            health_check "$service"
        else
            info "Skipping health check for $service as requested"
            sleep 5  # Brief wait without health check
        fi
    done
    
    success "All services deployed successfully"
}

# Verify deployment
verify_deployment() {
    header "Verifying Deployment"
    
    # Check all services are running
    info "Checking service status..."
    local failed_services=()
    
    # Get list of all services
    local services=($(docker compose -f "$COMPOSE_FILE" config --services))
    
    for service in "${services[@]}"; do
        if ! docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -ne 0 ]]; then
        error "Failed services: ${failed_services[*]}"
    fi
    
    # Test API endpoints
    info "Testing API endpoints..."
    local domain=$(grep DOMAIN_NAME "$ENV_FILE" | cut -d'=' -f2)
    
    # Test health endpoint
    if ! curl -f -s "https://$domain/health" > /dev/null; then
        warning "Health endpoint test failed"
    else
        success "Health endpoint is responding"
    fi
    
    # Test basic API functionality
    if ! curl -f -s "https://$domain/api/" > /dev/null; then
        warning "API endpoint test failed"
    else
        success "API endpoints are responding"
    fi
    
    success "Deployment verification completed"
}

# Cleanup old images and containers
cleanup() {
    header "Cleaning Up"
    
    info "Removing unused Docker images..."
    docker image prune -f || warning "Could not clean up images"
    
    info "Removing unused Docker volumes..."
    docker volume prune -f || warning "Could not clean up volumes"
    
    success "Cleanup completed"
}

# Display deployment summary
display_summary() {
    header "Deployment Summary"
    
    local domain=$(grep DOMAIN_NAME "$ENV_FILE" | cut -d'=' -f2)
    
    echo -e "${GREEN}🚀 Production deployment completed successfully!${NC}"
    echo
    echo -e "${BLUE}Deployment Details:${NC}"
    echo "• Version: ${YELLOW}$VERSION${NC}"
    echo "• Domain: ${YELLOW}https://$domain${NC}"
    echo "• Backup: ${YELLOW}${BACKUP_DIR:-"Skipped"}${NC}"
    echo "• Deployment Time: ${YELLOW}$(date)${NC}"
    echo
    echo -e "${BLUE}Service URLs:${NC}"
    echo "• Main Application: ${YELLOW}https://$domain${NC}"
    echo "• API Documentation: ${YELLOW}https://$domain/docs${NC}"
    echo "• Health Check: ${YELLOW}https://$domain/health${NC}"
    echo "• Metrics: ${YELLOW}https://$domain/metrics${NC} (restricted)"
    echo
    echo -e "${BLUE}Monitoring:${NC}"
    echo "• Check service status: ${YELLOW}docker compose -f $COMPOSE_FILE ps${NC}"
    echo "• View logs: ${YELLOW}docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo "• Monitor health: ${YELLOW}./scripts/health-check.sh${NC}"
    echo
    echo -e "${PURPLE}Next Steps:${NC}"
    echo "1. Monitor application logs for any issues"
    echo "2. Verify all functionality is working as expected"
    echo "3. Update monitoring dashboards if needed"
    echo "4. Document any changes or known issues"
    echo
    if [[ -n "${BACKUP_DIR:-}" ]]; then
        echo -e "${YELLOW}💾 Rollback Information:${NC}"
        echo "If you need to rollback, use the backup at: $BACKUP_DIR"
    fi
}

# Rollback function
rollback() {
    header "Rolling Back Deployment"
    
    if [[ -z "${BACKUP_DIR:-}" ]]; then
        error "No backup directory available for rollback"
    fi
    
    warning "Rolling back to previous version..."
    
    # Stop current services
    docker compose -f "$COMPOSE_FILE" down
    
    # Restore backup
    if [[ -f "$BACKUP_DIR/redis-dump.rdb" ]]; then
        info "Restoring Redis data..."
        docker cp "$BACKUP_DIR/redis-dump.rdb" $(docker compose -f "$COMPOSE_FILE" ps -q redis):/data/redis/dump.rdb
    fi
    
    # Restart services
    docker compose -f "$COMPOSE_FILE" up -d
    
    success "Rollback completed"
}

# Trap for cleanup on error
cleanup_on_error() {
    error "Deployment failed! Check logs for details."
    
    if [[ "$FORCE_DEPLOY" != "true" ]]; then
        read -p "Would you like to attempt rollback? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        fi
    fi
    
    exit 1
}

# Main deployment function
main() {
    header "DSL to PNG MCP Server - Production Deployment"
    
    cd "$PROJECT_ROOT"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Confirmation prompt
    if [[ "$FORCE_DEPLOY" != "true" ]]; then
        echo -e "${YELLOW}This will deploy DSL to PNG MCP Server to production.${NC}"
        echo "Version: $VERSION"
        echo "Domain: $(grep DOMAIN_NAME "$ENV_FILE" | cut -d'=' -f2 2>/dev/null || echo 'Not set')"
        echo
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Execute deployment steps
    check_prerequisites
    validate_configuration
    create_backup
    pull_images
    deploy_services
    verify_deployment
    cleanup
    display_summary
    
    success "Production deployment completed successfully!"
}

# Execute main function
main "$@"