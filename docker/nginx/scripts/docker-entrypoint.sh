#!/bin/bash
# =============================================================================
# Nginx Docker Entrypoint Script
# =============================================================================
# Custom entrypoint for Nginx container with SSL setup,
# configuration templating, and health checks
# =============================================================================

set -euo pipefail

# Configuration
NGINX_ENV="${NGINX_ENV:-development}"
DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
BACKEND_SERVERS="${BACKEND_SERVERS:-fastapi-server-1:8000,fastapi-server-2:8000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Info function
info() {
    log "${BLUE}INFO: $1${NC}"
}

# Warning function
warning() {
    log "${YELLOW}WARNING: $1${NC}"
}

# Generate self-signed certificate for development
generate_dev_certificate() {
    info "Generating self-signed certificate for development..."
    
    mkdir -p /etc/nginx/ssl
    
    if [ ! -f "/etc/nginx/ssl/dev-cert.pem" ] || [ ! -f "/etc/nginx/ssl/dev-key.pem" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/nginx/ssl/dev-key.pem \
            -out /etc/nginx/ssl/dev-cert.pem \
            -subj "/C=US/ST=Development/L=Development/O=DSL-PNG/OU=Development/CN=localhost"
        
        chmod 600 /etc/nginx/ssl/dev-key.pem
        chmod 644 /etc/nginx/ssl/dev-cert.pem
        
        success "Self-signed certificate generated"
    else
        info "Self-signed certificate already exists"
    fi
}

# Setup Let's Encrypt certificate for production
setup_letsencrypt() {
    info "Setting up Let's Encrypt certificate for production..."
    
    if [ "$DOMAIN_NAME" = "localhost" ]; then
        warning "Domain name is localhost, skipping Let's Encrypt setup"
        return 0
    fi
    
    # Check if certificate already exists
    if [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
        info "Let's Encrypt certificate already exists for $DOMAIN_NAME"
        return 0
    fi
    
    # Create webroot directory
    mkdir -p /var/www/html/.well-known/acme-challenge
    
    # Start nginx with HTTP-only configuration for certificate generation
    info "Starting Nginx in HTTP-only mode for certificate generation..."
    
    # Create temporary HTTP-only configuration
    cat > /etc/nginx/conf.d/temp-http.conf << EOF
server {
    listen 80 default_server;
    server_name $DOMAIN_NAME;
    root /var/www/html;
    
    location /.well-known/acme-challenge/ {
        try_files \$uri =404;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF
    
    # Test nginx configuration
    nginx -t || error "Nginx configuration test failed"
    
    # Start nginx in background
    nginx -g "daemon off;" &
    NGINX_PID=$!
    
    # Wait for nginx to start
    sleep 5
    
    # Request certificate
    info "Requesting Let's Encrypt certificate for $DOMAIN_NAME..."
    
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/html \
        --email admin@$DOMAIN_NAME \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        -d $DOMAIN_NAME
    
    # Stop temporary nginx
    kill $NGINX_PID || true
    wait $NGINX_PID 2>/dev/null || true
    
    # Remove temporary configuration
    rm -f /etc/nginx/conf.d/temp-http.conf
    
    success "Let's Encrypt certificate obtained for $DOMAIN_NAME"
}

# Template configuration files
template_configurations() {
    info "Templating Nginx configurations..."
    
    # Template production configuration
    if [ -f "/etc/nginx/conf.d/prod.conf" ]; then
        sed -i "s/\${DOMAIN_NAME}/$DOMAIN_NAME/g" /etc/nginx/conf.d/prod.conf
        info "Production configuration templated"
    fi
    
    # Update upstream servers if provided
    if [ -n "$BACKEND_SERVERS" ]; then
        info "Updating backend servers: $BACKEND_SERVERS"
        
        # Create upstream configuration
        cat > /etc/nginx/conf.d/upstream.conf << EOF
upstream fastapi_backend {
    least_conn;
EOF
        
        IFS=',' read -ra SERVERS <<< "$BACKEND_SERVERS"
        for server in "${SERVERS[@]}"; do
            echo "    server $server max_fails=3 fail_timeout=30s;" >> /etc/nginx/conf.d/upstream.conf
        done
        
        cat >> /etc/nginx/conf.d/upstream.conf << EOF
    keepalive 32;
}
EOF
    fi
}

# Setup log rotation
setup_log_rotation() {
    info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/nginx << EOF
/var/log/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 nginx nginx
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 \$(cat /var/run/nginx.pid)
        fi
    endscript
}
EOF
    
    success "Log rotation configured"
}

# Create necessary directories
create_directories() {
    info "Creating necessary directories..."
    
    mkdir -p /var/log/nginx
    mkdir -p /var/cache/nginx
    mkdir -p /var/www/html
    mkdir -p /var/www/static/png
    mkdir -p /etc/nginx/ssl
    
    # Set proper permissions (ignore read-only filesystem errors)
    chown -R nginx:nginx /var/log/nginx 2>/dev/null || true
    chown -R nginx:nginx /var/cache/nginx 2>/dev/null || true
    chown -R nginx:nginx /var/www 2>/dev/null || true
    
    success "Directories created and permissions set"
}

# Wait for backend services
wait_for_backends() {
    info "Waiting for backend services to be ready..."
    
    IFS=',' read -ra SERVERS <<< "$BACKEND_SERVERS"
    for server in "${SERVERS[@]}"; do
        IFS=':' read -ra HOST_PORT <<< "$server"
        host="${HOST_PORT[0]}"
        port="${HOST_PORT[1]:-8000}"
        
        info "Waiting for $host:$port..."
        
        timeout=60
        while [ $timeout -gt 0 ]; do
            if nc -z "$host" "$port" 2>/dev/null; then
                success "$host:$port is ready"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            warning "$host:$port is not ready, continuing anyway"
        fi
    done
}

# Test nginx configuration
test_configuration() {
    info "Testing Nginx configuration..."
    
    if nginx -t; then
        success "Nginx configuration test passed"
    else
        error "Nginx configuration test failed"
    fi
}

# Setup health check endpoint
setup_health_check() {
    info "Setting up health check endpoint..."
    
    # Try to create health check files, ignore read-only filesystem errors
    cat > /var/www/html/health << EOF 2>/dev/null || true
healthy
EOF
    
    cat > /var/www/html/index.html << EOF 2>/dev/null || true
<!DOCTYPE html>
<html>
<head>
    <title>DSL to PNG MCP Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .healthy { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DSL to PNG MCP Server</h1>
        <div class="status healthy">
            ✓ Nginx Proxy is running
        </div>
        <p>Environment: <strong>$NGINX_ENV</strong></p>
        <p>Domain: <strong>$DOMAIN_NAME</strong></p>
        <p>Backend Servers: <strong>$BACKEND_SERVERS</strong></p>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/docs">API Documentation</a></li>
            <li><a href="/metrics">Metrics</a> (restricted)</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    success "Health check endpoint configured"
}

# Main entrypoint function
main() {
    info "Starting Nginx entrypoint script..."
    info "Environment: $NGINX_ENV"
    info "Domain: $DOMAIN_NAME"
    info "Backend Servers: $BACKEND_SERVERS"
    
    # Create directories
    create_directories
    
    # Setup health check
    setup_health_check
    
    # Template configurations
    template_configurations
    
    # Environment-specific setup
    case "$NGINX_ENV" in
        "development")
            info "Setting up development environment..."
            generate_dev_certificate
            ;;
        "production")
            info "Setting up production environment..."
            setup_letsencrypt
            setup_log_rotation
            ;;
        *)
            warning "Unknown environment: $NGINX_ENV, using development settings"
            generate_dev_certificate
            ;;
    esac
    
    # Wait for backend services (optional in development)
    if [ "$NGINX_ENV" = "production" ]; then
        wait_for_backends
    fi
    
    # Test configuration
    test_configuration
    
    success "Nginx entrypoint setup completed"
    
    # Execute the original command (nginx)
    info "Starting Nginx..."
    exec "$@"
}

# Check if running as nginx user
if [ "$(id -u)" = "0" ]; then
    # If running as root, setup and then switch to nginx user
    main "$@"
else
    # If already running as nginx user, just start nginx
    exec "$@"
fi