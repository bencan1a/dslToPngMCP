#!/bin/bash
# =============================================================================
# Development Environment Setup Script
# =============================================================================
# Sets up the complete development environment for DSL to PNG MCP Server
# Creates necessary directories, generates secrets, and initializes services
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.development"

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

# Check prerequisites
check_prerequisites() {
    header "Checking Prerequisites"
    
    local missing_tools=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    else
        info "Docker: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_tools+=("docker compose")
    else
        if command -v docker compose &> /dev/null; then
            info "Docker Compose: $(docker compose --version)"
        else
            info "Docker Compose: $(docker compose version)"
        fi
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    else
        info "Git: $(git --version)"
    fi
    
    # Check Make (optional but recommended)
    if command -v make &> /dev/null; then
        info "Make: $(make --version | head -1)"
    else
        warning "Make not found (optional but recommended)"
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
    fi
    
    success "All prerequisites satisfied"
}

# Create directory structure
create_directories() {
    header "Creating Directory Structure"
    
    info "Creating data directories..."
    mkdir -p "$PROJECT_ROOT/data/redis"
    mkdir -p "$PROJECT_ROOT/data/storage/png"
    mkdir -p "$PROJECT_ROOT/data/monitoring/prometheus"
    mkdir -p "$PROJECT_ROOT/data/monitoring/grafana"
    
    info "Creating log directories..."
    mkdir -p "$PROJECT_ROOT/logs/nginx"
    mkdir -p "$PROJECT_ROOT/logs/mcp"
    mkdir -p "$PROJECT_ROOT/logs/fastapi"
    mkdir -p "$PROJECT_ROOT/logs/celery"
    mkdir -p "$PROJECT_ROOT/logs/playwright"
    mkdir -p "$PROJECT_ROOT/logs/redis"
    
    info "Creating configuration directories..."
    mkdir -p "$PROJECT_ROOT/docker/config"
    mkdir -p "$PROJECT_ROOT/docker/nginx/html"
    mkdir -p "$PROJECT_ROOT/docker/nginx/ssl"
    mkdir -p "$PROJECT_ROOT/secrets"
    mkdir -p "$PROJECT_ROOT/backups"
    
    success "Directory structure created"
}

# Generate development secrets
generate_secrets() {
    header "Generating Development Secrets"
    
    # Generate app secret key
    if [ ! -f "$PROJECT_ROOT/secrets/app_secret_key.txt" ]; then
        info "Generating application secret key..."
        openssl rand -base64 32 > "$PROJECT_ROOT/secrets/app_secret_key.txt"
        chmod 600 "$PROJECT_ROOT/secrets/app_secret_key.txt"
    else
        info "Application secret key already exists"
    fi
    
    # Generate Redis password
    if [ ! -f "$PROJECT_ROOT/secrets/redis_password.txt" ]; then
        info "Generating Redis password..."
        echo "devpassword" > "$PROJECT_ROOT/secrets/redis_password.txt"
        chmod 600 "$PROJECT_ROOT/secrets/redis_password.txt"
    else
        info "Redis password already exists"
    fi
    
    # Generate Grafana password
    if [ ! -f "$PROJECT_ROOT/secrets/grafana_password.txt" ]; then
        info "Generating Grafana password..."
        echo "admin" > "$PROJECT_ROOT/secrets/grafana_password.txt"
        chmod 600 "$PROJECT_ROOT/secrets/grafana_password.txt"
    else
        info "Grafana password already exists"
    fi
    
    success "Development secrets generated"
}

# Create configuration files
create_configurations() {
    header "Creating Configuration Files"
    
    # Create MCP development config
    info "Creating MCP server configuration..."
    cat > "$PROJECT_ROOT/docker/config/mcp-dev.env" << EOF
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_LOG_LEVEL=DEBUG
DSL_PNG_MCP_HOST=0.0.0.0
DSL_PNG_MCP_PORT=3001
EOF
    
    # Create FastAPI development config
    info "Creating FastAPI server configuration..."
    cat > "$PROJECT_ROOT/docker/config/fastapi-dev.env" << EOF
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_LOG_LEVEL=DEBUG
DSL_PNG_HOST=0.0.0.0
DSL_PNG_PORT=8000
DSL_PNG_ENABLE_DOCS=true
DSL_PNG_ENABLE_REDOC=true
EOF
    
    # Create Celery development config
    info "Creating Celery worker configuration..."
    cat > "$PROJECT_ROOT/docker/config/celery-dev.env" << EOF
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_LOG_LEVEL=DEBUG
CELERY_LOG_LEVEL=DEBUG
CELERY_CONCURRENCY=2
EOF
    
    # Create Playwright development config
    info "Creating Playwright configuration..."
    cat > "$PROJECT_ROOT/docker/config/playwright-dev.env" << EOF
DSL_PNG_ENVIRONMENT=development
DSL_PNG_DEBUG=true
DSL_PNG_PLAYWRIGHT_HEADLESS=true
DSL_PNG_BROWSER_POOL_SIZE=3
EOF
    
    success "Configuration files created"
}

# Generate SSL certificates for development
generate_ssl_certificates() {
    header "Generating SSL Certificates for Development"
    
    if [ ! -f "$PROJECT_ROOT/docker/nginx/ssl/dev-cert.pem" ]; then
        info "Generating self-signed SSL certificate..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$PROJECT_ROOT/docker/nginx/ssl/dev-key.pem" \
            -out "$PROJECT_ROOT/docker/nginx/ssl/dev-cert.pem" \
            -subj "/C=US/ST=Development/L=Development/O=DSL-PNG/OU=Development/CN=localhost" \
            -config <(
                echo '[req]'
                echo 'default_bits = 2048'
                echo 'prompt = no'
                echo 'default_md = sha256'
                echo 'distinguished_name = dn'
                echo 'req_extensions = v3_req'
                echo '[dn]'
                echo 'C=US'
                echo 'ST=Development'
                echo 'L=Development'
                echo 'O=DSL-PNG'
                echo 'OU=Development'
                echo 'CN=localhost'
                echo '[v3_req]'
                echo 'basicConstraints = CA:FALSE'
                echo 'keyUsage = nonRepudiation, digitalSignature, keyEncipherment'
                echo 'subjectAltName = @alt_names'
                echo '[alt_names]'
                echo 'DNS.1 = localhost'
                echo 'DNS.2 = *.localhost'
                echo 'IP.1 = 127.0.0.1'
                echo 'IP.2 = ::1'
            )
        
        chmod 600 "$PROJECT_ROOT/docker/nginx/ssl/dev-key.pem"
        chmod 644 "$PROJECT_ROOT/docker/nginx/ssl/dev-cert.pem"
        
        success "SSL certificate generated"
    else
        info "SSL certificate already exists"
    fi
}

# Create HTML files for nginx
create_html_files() {
    header "Creating HTML Files"
    
    # Create index.html
    info "Creating index.html..."
    cat > "$PROJECT_ROOT/docker/nginx/html/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DSL to PNG MCP Server - Development</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .content {
            padding: 30px;
        }
        .status {
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            display: flex;
            align-items: center;
        }
        .healthy {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .info {
            background-color: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }
        .link-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-decoration: none;
            color: #495057;
            transition: all 0.2s;
        }
        .link-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .link-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .link-desc {
            font-size: 0.9em;
            color: #6c757d;
        }
        .icon {
            margin-right: 10px;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 DSL to PNG MCP Server</h1>
            <p>Development Environment</p>
        </div>
        <div class="content">
            <div class="status healthy">
                <span class="icon">✅</span>
                <span>Nginx reverse proxy is running successfully</span>
            </div>
            
            <div class="info">
                <span class="icon">ℹ️</span>
                <span>Environment: <strong>Development</strong> | Version: <strong>1.0.0</strong></span>
            </div>
            
            <div class="links">
                <a href="/health" class="link-card">
                    <div class="link-title">🏥 Health Check</div>
                    <div class="link-desc">System health status</div>
                </a>
                
                <a href="/docs" class="link-card">
                    <div class="link-title">📚 API Documentation</div>
                    <div class="link-desc">Interactive API docs</div>
                </a>
                
                <a href="/redoc" class="link-card">
                    <div class="link-title">📖 ReDoc</div>
                    <div class="link-desc">Alternative API docs</div>
                </a>
                
                <a href="/static/png/" class="link-card">
                    <div class="link-title">🖼️ PNG Storage</div>
                    <div class="link-desc">Generated PNG files</div>
                </a>
                
                <a href="/metrics" class="link-card">
                    <div class="link-title">📊 Metrics</div>
                    <div class="link-desc">Performance metrics</div>
                </a>
                
                <a href="/nginx-status" class="link-card">
                    <div class="link-title">⚙️ Nginx Status</div>
                    <div class="link-desc">Nginx server status</div>
                </a>
            </div>
        </div>
    </div>
</body>
</html>
EOF
    
    # Create 404.html
    cat > "$PROJECT_ROOT/docker/nginx/html/404.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .error { color: #e74c3c; font-size: 48px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="error">404</div>
    <h1>Page Not Found</h1>
    <p>The requested page could not be found.</p>
    <a href="/">Go back to home</a>
</body>
</html>
EOF
    
    # Create 50x.html
    cat > "$PROJECT_ROOT/docker/nginx/html/50x.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Server Error</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .error { color: #e74c3c; font-size: 48px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="error">5xx</div>
    <h1>Server Error</h1>
    <p>The server encountered an error and could not complete your request.</p>
    <a href="/">Go back to home</a>
</body>
</html>
EOF
    
    success "HTML files created"
}

# Set proper permissions
set_permissions() {
    header "Setting Permissions"
    
    info "Setting directory permissions..."
    chmod -R 755 "$PROJECT_ROOT/data"
    chmod -R 755 "$PROJECT_ROOT/logs"
    chmod -R 700 "$PROJECT_ROOT/secrets"
    
    info "Setting script permissions..."
    find "$PROJECT_ROOT/scripts" -name "*.sh" -exec chmod +x {} \;
    find "$PROJECT_ROOT/docker" -name "*.sh" -exec chmod +x {} \;
    
    success "Permissions set"
}

# Create development environment file
create_env_file() {
    header "Creating Environment File"
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        info "Creating .env file from development template..."
        cp "$ENV_FILE" "$PROJECT_ROOT/.env"
        success "Environment file created"
    else
        info "Environment file already exists"
    fi
}

# Build Docker images
build_images() {
    header "Building Docker Images"
    
    cd "$PROJECT_ROOT"
    
    info "Building Docker images for development..."
    docker compose build --parallel
    
    success "Docker images built successfully"
}

# Display setup summary
display_summary() {
    header "Setup Complete!"
    
    echo -e "${GREEN}✅ Development environment setup completed successfully!${NC}"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Start the development environment:"
    echo "   ${YELLOW}cd $PROJECT_ROOT && docker compose up -d${NC}"
    echo
    echo "2. Check service status:"
    echo "   ${YELLOW}docker compose ps${NC}"
    echo
    echo "3. View logs:"
    echo "   ${YELLOW}docker compose logs -f${NC}"
    echo
    echo "4. Access the application:"
    echo "   • HTTP:  ${YELLOW}http://localhost${NC}"
    echo "   • HTTPS: ${YELLOW}https://localhost${NC} (self-signed cert)"
    echo "   • API Docs: ${YELLOW}http://localhost/docs${NC}"
    echo
    echo "5. Stop the environment:"
    echo "   ${YELLOW}docker compose down${NC}"
    echo
    echo -e "${PURPLE}Development credentials:${NC}"
    echo "• Redis password: ${YELLOW}devpassword${NC}"
    echo "• Grafana admin password: ${YELLOW}admin${NC}"
    echo
    echo -e "${BLUE}For more information, see the documentation in the docs/ directory.${NC}"
}

# Main setup function
main() {
    header "DSL to PNG MCP Server - Development Setup"
    
    cd "$PROJECT_ROOT"
    
    check_prerequisites
    create_directories
    generate_secrets
    create_configurations
    generate_ssl_certificates
    create_html_files
    set_permissions
    create_env_file
    build_images
    display_summary
    
    success "Development environment setup completed!"
}

# Handle script interruption
trap 'error "Setup interrupted by user"' INT TERM

# Execute main function
main "$@"