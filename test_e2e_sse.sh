#!/bin/bash
#
# End-to-End SSE Pipeline Test Script
# ===================================
#
# This script tests the complete SSE pipeline using the development environment by:
# 1. Starting the required services (Redis, FastAPI server, Nginx proxy)
# 2. Running the E2E SSE test locally against the running services
# 3. Saving the PNG output with a timestamp to test-results/
#
# Usage:
#   ./test_e2e_sse.sh <dsl_input_file>
#
# Examples:
#   ./test_e2e_sse.sh examples/simple_button.json
#   ./test_e2e_sse.sh examples/dashboard.json
#   ./test_e2e_sse.sh examples/mobile_app.yaml
#
# Requirements:
#   - Python3 with aiohttp library
#   - Docker and Docker Compose
#   - Access to development environment services
#

set -e  # Exit on any error

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yaml"
OUTPUT_DIR="test-results"
TEST_SCRIPT="test_e2e_sse.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check arguments
if [ $# -ne 1 ]; then
    log_error "Usage: $0 <dsl_input_file>"
    log_info "Examples:"
    log_info "  $0 examples/simple_button.json"
    log_info "  $0 examples/dashboard.json"
    log_info "  $0 examples/mobile_app.yaml"
    exit 1
fi

DSL_INPUT="$1"

# Validate input file exists
if [ ! -f "$DSL_INPUT" ]; then
    log_error "DSL input file not found: $DSL_INPUT"
    exit 1
fi

log_info "Starting E2E SSE Pipeline Test"
log_info "DSL Input: $DSL_INPUT"
log_info "Output Directory: $OUTPUT_DIR"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Check if Docker Compose file exists
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    log_error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    exit 1
fi

# Start services in background (development environment)
log_info "Starting Docker services (Redis, FastAPI server, Nginx proxy)..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d redis fastapi-server-1 nginx-proxy

# Wait for services to be ready
log_info "Waiting for services to be ready..."
sleep 20

# Check if services are running (simplified check without jq dependency)
log_info "Checking if services are running..."
redis_running=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps redis --format "table" | grep -c "Up" || echo "0")
fastapi_running=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps fastapi-server-1 --format "table" | grep -c "Up" || echo "0")
nginx_running=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps nginx-proxy --format "table" | grep -c "Up" || echo "0")

if [ "$redis_running" -gt "0" ]; then
    log_info "Redis: Running"
else
    log_warning "Redis: Not running"
fi

if [ "$fastapi_running" -gt "0" ]; then
    log_info "FastAPI Server: Running"
else
    log_warning "FastAPI Server: Not running"
fi

if [ "$nginx_running" -gt "0" ]; then
    log_info "Nginx Proxy: Running"
else
    log_warning "Nginx Proxy: Not running"
fi

# Wait for API server to be ready
log_info "Waiting for API server to be ready..."
sleep 15

# Check API server health (via nginx proxy)
API_URL="http://localhost"
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    log_info "Checking API server health (attempt $attempt/$max_attempts)..."
    
    if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        log_success "API server is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "API server failed to start after $max_attempts attempts"
        log_info "Showing FastAPI server logs:"
        docker compose -f "$DOCKER_COMPOSE_FILE" logs fastapi-server-1
        log_info "Showing Nginx proxy logs:"
        docker compose -f "$DOCKER_COMPOSE_FILE" logs nginx-proxy || true
        exit 1
    fi
    
    sleep 3
    ((attempt++))
done

# Run the E2E test locally with access to the Docker services
log_info "Running E2E SSE test..."

# Create a temporary container with access to the running services
DSL_BASENAME=$(basename "$DSL_INPUT")

# Create test environment with aiohttp
log_info "Installing Python dependencies for test..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 is required to run the E2E test"
    exit 1
fi

# Set up Python environment
PYTHON_CMD="python3"
PIP_CMD="pip3"

# Activate virtual environment if it exists and update commands
if [ -f "bin/activate" ]; then
    log_info "Activating virtual environment..."
    source bin/activate
    # Use the activated environment's python and pip
    PYTHON_CMD="python"
    PIP_CMD="pip"
    
    # Debug: Show which Python is being used after activation
    log_info "Virtual environment activated. Python path: $(which python)"
    log_info "Python version: $($PYTHON_CMD --version)"
    log_info "Virtual environment: $VIRTUAL_ENV"
else
    log_info "No virtual environment found at bin/activate, using system Python"
fi

# Debug: Show Python command that will be used
log_info "Python command to be used: $PYTHON_CMD ($(which $PYTHON_CMD))"

# Check for aiohttp in the current environment
if ! $PYTHON_CMD -c "import aiohttp" 2>/dev/null; then
    log_info "Installing aiohttp..."
    $PIP_CMD install aiohttp>=3.9.0 || {
        log_error "Failed to install aiohttp. Please install manually: $PIP_CMD install aiohttp>=3.9.0"
        exit 1
    }
fi

# Verify aiohttp installation
if ! $PYTHON_CMD -c "import aiohttp; print(f'aiohttp {aiohttp.__version__} is available')" 2>/dev/null; then
    log_error "aiohttp installation verification failed"
    exit 1
fi

# Run the test locally using the same Python environment
log_info "Executing test script..."
log_info "Command: $PYTHON_CMD $TEST_SCRIPT $DSL_INPUT --server localhost"
log_info "Working directory: $(pwd)"
log_info "PYTHONPATH: ${PYTHONPATH:-not set}"

# Add timeout and verbose execution
log_info "Starting Python script execution with timeout..."
timeout 120 $PYTHON_CMD "$TEST_SCRIPT" "$DSL_INPUT" --server localhost &
python_pid=$!

log_info "Python script PID: $python_pid"
log_info "Waiting for Python script to complete..."

# Wait for the process and capture exit code
wait $python_pid
test_exit_code=$?

if [ $test_exit_code -eq 124 ]; then
    log_error "Python script timed out after 120 seconds"
elif [ $test_exit_code -ne 0 ]; then
    log_error "Python script failed with exit code: $test_exit_code"
else
    log_success "Python script completed successfully"
fi

# Check for generated files
log_info "Checking for generated PNG files..."
if ls "$OUTPUT_DIR"/*.png > /dev/null 2>&1; then
    log_success "PNG files generated in $OUTPUT_DIR/"
    
    # List generated files
    log_info "Generated files:"
    ls -la "$OUTPUT_DIR"/*.png 2>/dev/null | tail -n +2 | while read -r line; do
        log_info "  $line"
    done
else
    log_warning "No PNG files found in $OUTPUT_DIR/"
fi

# Cleanup (optional - comment out if you want to keep containers running)
log_info "Cleaning up Docker containers..."
docker compose -f "$DOCKER_COMPOSE_FILE" down

# Report results
if [ $test_exit_code -eq 0 ]; then
    log_success "E2E SSE Pipeline Test PASSED!"
    log_info "Check the test-results/ directory for generated PNG files"
else
    log_error "E2E SSE Pipeline Test FAILED!"
    log_info "Check the logs above for error details"
fi

exit $test_exit_code