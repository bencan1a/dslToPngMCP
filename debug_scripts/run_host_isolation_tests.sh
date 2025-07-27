#!/bin/bash

# =============================================================================
# Run Isolation Tests from Host with Development Browser Support
# =============================================================================
# This script runs the isolation tests from the host environment while
# optionally leveraging the browser service from development infrastructure
# 
# IMPORTANT: These are still ISOLATION TESTS that bypass infrastructure!
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    echo "=============================================================="
    echo "$1"
    echo "=============================================================="
}

print_header "🧪 SSE Server Isolation Testing from Host"

# Check if we're in the project root
if [ ! -f "docker-compose.yaml" ]; then
    print_status $RED "❌ docker-compose.yaml not found. Run this script from the project root."
    exit 1
fi

print_status $GREEN "✅ Found project root"

# Check Python availability
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_status $RED "❌ Python is not available"
    exit 1
fi

print_status $GREEN "✅ Python available: $PYTHON_CMD"

# Check if isolation test scripts exist
ISOLATION_SCRIPTS=(
    "debug_scripts/test_component_isolation.py"
    "debug_scripts/test_mcp_tool_direct.py" 
    "debug_scripts/test_sse_server_direct.py"
    "debug_scripts/test_sse_mock_infrastructure.py"
)

MISSING_SCRIPTS=""
for script in "${ISOLATION_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        MISSING_SCRIPTS="$MISSING_SCRIPTS $script"
    fi
done

if [ ! -z "$MISSING_SCRIPTS" ]; then
    print_status $RED "❌ Missing isolation test scripts:$MISSING_SCRIPTS"
    exit 1
fi

print_status $GREEN "✅ All isolation test scripts found"

# Optional: Check if browser service is running (for PNG generation)
print_header "🌐 Checking Browser Service (Optional)"

if command -v docker &> /dev/null; then
    BROWSER_RUNNING=$(docker ps --filter "name=dsl-browsers-dev" --filter "status=running" -q)
    
    if [ ! -z "$BROWSER_RUNNING" ]; then
        print_status $GREEN "✅ Browser service is running (PNG tests will work)"
    else
        print_status $YELLOW "⚠️  Browser service not running"
        print_status $BLUE "💡 PNG generation tests may fail"
        print_status $BLUE "💡 Run 'docker compose up -d' to start browser service"
        print_status $BLUE "💡 Other isolation tests will still work fine"
    fi
else
    print_status $YELLOW "⚠️  Docker not available - browser checks skipped"
fi

# Run isolation tests
print_header "🔬 Running Isolation Tests"

print_status $BLUE "🎯 These tests BYPASS all infrastructure (nginx/redis/fastapi)"
print_status $BLUE "🎯 They test components in complete isolation"
print_status $BLUE "🎯 Only browser service is used for PNG generation (if available)"

echo
echo "Starting isolation test execution..."
echo

$PYTHON_CMD debug_scripts/run_isolation_tests_with_dev_browsers.py

# Check exit code
if [ $? -eq 0 ]; then
    print_status $GREEN "✅ Isolation tests completed"
else
    print_status $YELLOW "⚠️  Isolation tests completed with issues"
fi

print_header "📋 What These Tests Tell Us"

echo "✅ ISOLATION TESTING means:"
echo "   • Components tested completely independently"
echo "   • All infrastructure (Redis/FastAPI/nginx) is mocked/bypassed"  
echo "   • Tests show if the bug is in component logic itself"
echo
echo "🎯 If NoneType errors are reproduced in isolation:"
echo "   → The bug is in core component logic (not infrastructure)"
echo "   → Focus debugging on DSL parsing, MCP tools, or SSE logic"
echo
echo "🎯 If isolation tests pass but real system fails:"
echo "   → The bug is in infrastructure integration"
echo "   → Focus on Redis connections, FastAPI routing, etc."
echo
echo "📝 Next steps based on results:"
echo "   1. Check individual test outputs above"
echo "   2. Focus debugging on components that failed in isolation"
echo "   3. Use successful isolation results to rule out component issues"

print_status $BLUE "🚀 Use these results to target your debugging!"