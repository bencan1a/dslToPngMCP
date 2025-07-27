# Debug Scripts - SSE Server Isolation Testing

This directory contains targeted isolation testing scripts to debug the "Invalid input of type: 'NoneType'" error in the DSL to PNG MCP Server SSE functionality.

## 🎯 Purpose

These scripts isolate the SSE server components from FastAPI, Redis, and Nginx infrastructure to determine the exact source of NoneType errors when processing `examples/simple_button.json`.

## 📁 Scripts Overview

### 1. `test_sse_server_direct.py`
**Purpose**: Test SSE server components directly, bypassing FastAPI routing

**What it tests**:
- SSE MCP Bridge functionality without HTTP layer
- SSE Connection Manager without real WebSocket connections  
- SSE Event processing models
- MCP Bridge execute_tool_with_sse method

**Key Goal**: Determine if the NoneType error is in SSE server core logic

### 2. `test_mcp_tool_direct.py`
**Purpose**: Test MCP server tools directly, bypassing all HTTP/SSE infrastructure

**What it tests**:
- MCP Server initialization and tool discovery
- Direct MCP tool calls (`render_ui_mockup`)
- Internal MCP handler methods (`_handle_render_ui_mockup`)
- Individual rendering pipeline steps (DSL parsing, HTML generation, PNG generation)

**Key Goal**: Determine if the NoneType error is in the MCP tools themselves

### 3. `test_component_isolation.py`
**Purpose**: Test each component individually to isolate exactly which component fails

**What it tests**:
- Models and Schemas (DSLDocument, ElementLayout, etc.)
- Settings and Configuration loading
- DSL Parser component isolation
- HTML Generator component isolation
- PNG Generator component isolation (with mocks)

**Key Goal**: Identify exactly which component fails with NoneType error

### 4. `test_sse_mock_infrastructure.py`
**Purpose**: Test SSE functionality with mocked infrastructure dependencies

**What it tests**:
- Mock Redis/database connections
- Mock SSE Connection Manager
- Mock MCP Server with successful responses
- Complete SSE pipeline with all infrastructure mocked

**Key Goal**: Determine if infrastructure dependencies are causing the issue

## 🔍 Test Data

All scripts use the exact `simple_button.json` content that's causing the issue:

```json
{
  "title": "Simple Button Example",
  "description": "A basic button demonstration", 
  "width": 400,
  "height": 200,
  "elements": [
    {
      "type": "button",
      "id": "primary-btn",
      "layout": {
        "x": 150,
        "y": 80,
        "width": 100,
        "height": 40
      },
      "style": {
        "background": "#007bff",
        "color": "white",
        "fontSize": 16,
        "fontWeight": "bold",
        "borderRadius": "8px"
      },
      "label": "Click Me!",
      "onClick": "handleClick()"
    }
  ],
  "css": ".dsl-button:hover { transform: scale(1.05); transition: transform 0.2s; }"
}
```

## 🚀 Usage

### Option 1: Docker Test Environment (Recommended)
```bash
# Run isolation tests in Docker test environment (now with debug_scripts mounted!)
docker compose -f docker/docker-compose.test.yml run test python debug_scripts/test_component_isolation.py

# Or run individual tests
docker compose -f docker/docker-compose.test.yml run test python debug_scripts/test_mcp_tool_direct.py
docker compose -f docker/docker-compose.test.yml run test python debug_scripts/test_sse_server_direct.py
docker compose -f docker/docker-compose.test.yml run test python debug_scripts/test_sse_mock_infrastructure.py
```

### Option 2: Host with Development Infrastructure
```bash
# 1. Start development infrastructure
docker compose up -d

# 2. Run isolation tests from host (still bypasses nginx/redis/fastapi!)
./debug_scripts/run_host_isolation_tests.sh

# Or run the Python launcher directly
python3 debug_scripts/run_isolation_tests_with_dev_browsers.py
```

**Key Benefits of Host Testing:**
- ✅ **Still pure isolation testing** (bypasses nginx/redis/fastapi)
- ✅ Faster iteration during debugging
- ✅ Can optionally use development browser service for PNG generation
- ✅ Direct access to host Python environment and debugging tools

### Option 3: Individual Script Execution

```bash
# Test SSE server components directly
python debug_scripts/test_sse_server_direct.py

# Test MCP tools directly
python debug_scripts/test_mcp_tool_direct.py

# Test individual components
python debug_scripts/test_component_isolation.py

# Test with mock infrastructure
python debug_scripts/test_sse_mock_infrastructure.py
```

### Running All Scripts (Traditional)

```bash
# Run all isolation tests sequentially
for script in debug_scripts/test_*.py; do
    echo "========================================="
    echo "Running: $script"
    echo "========================================="
    python "$script"
    echo
done
```

## 📊 Expected Output

Each script provides:

1. **Detailed logging** of each test step
2. **Clear pass/fail indicators** (✓ PASS / ❌ FAIL)
3. **NoneType error detection** with specific location identification
4. **Analysis section** explaining what the results mean

### Sample Output Format

```
🔍 DIRECT SSE SERVER ISOLATION TESTS
Purpose: Test SSE server components without FastAPI/HTTP layer
Goal: Isolate the source of 'NoneType' errors

============================================================
TESTING: SSE MCP Bridge Direct Call
============================================================
[INFO] Initializing MCP Bridge...
[INFO] ✓ MCP Bridge initialized successfully
...

============================================================
TEST RESULTS SUMMARY
============================================================
connection_manager    ✓ PASS
event_processing     ✓ PASS  
mcp_bridge          ❌ FAIL
  → mcp_bridge returned None (potential NoneType source)

============================================================
ANALYSIS
============================================================
🎯 POTENTIAL ISSUE FOUND: MCP Bridge returns None
   This suggests the NoneType error originates in the MCP tools layer
```

## 🔧 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root directory
2. **Missing Dependencies**: Scripts are designed to work with minimal dependencies, but core project modules must be available
3. **Environment Variables**: Some scripts may need basic environment setup

### Environment Setup

```bash
# Ensure you're in the project root
cd /home/devcontainers/dslToPngMCP

# Set Python path if needed
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run scripts
python debug_scripts/test_sse_server_direct.py
```

## 🎯 Debugging Strategy

Use these scripts in order to narrow down the issue:

### 1. Start with Component Isolation
```bash
python debug_scripts/test_component_isolation.py
```
This identifies if basic components (models, parsers, etc.) work.

### 2. Test MCP Tools Directly  
```bash
python debug_scripts/test_mcp_tool_direct.py
```
This isolates whether the issue is in MCP tool logic.

### 3. Test SSE Server Components
```bash
python debug_scripts/test_sse_server_direct.py
```
This tests SSE-specific logic without HTTP infrastructure.

### 4. Test with Mock Infrastructure
```bash
python debug_scripts/test_sse_mock_infrastructure.py
```
This determines if real infrastructure dependencies are the problem.

## 🔎 What Each Result Means

| Test Result | Meaning | Next Steps |
|-------------|---------|------------|
| Component Isolation Fails | Basic data models or parsers have issues | Check schema definitions, imports |
| MCP Tools Fail | Core rendering logic has problems | Debug DSL parsing, HTML/PNG generation |
| SSE Server Fails | SSE-specific logic has issues | Check SSE bridge, connection manager |
| Mock Infrastructure Works | Real infrastructure is the problem | Check Redis, PostgreSQL, browser pool |

## 📝 Logging

All scripts use detailed logging to help identify exactly where failures occur:

- **DEBUG level**: Detailed step-by-step execution
- **INFO level**: Major milestones and success indicators  
- **ERROR level**: Failures with full tracebacks
- **Special markers**: 🔍 for diagnostic info, ❌ for failures, ✓ for success

## 🎯 Key Goals

These scripts will definitively determine whether the NoneType error is in:

- ✅ SSE server core logic itself
- ✅ Interaction with FastAPI/HTTP layer  
- ✅ Redis connectivity/state management
- ✅ Underlying MCP tools/DSL processing
- ✅ Basic component/model issues
- ✅ Infrastructure dependency problems

## ⚠️ Important Notes

1. **These are isolation tests**: They bypass normal infrastructure to isolate specific components
2. **Expected failures**: Some tests (like PNG generation) may fail due to missing browser dependencies - this is expected and documented
3. **Focus on NoneType**: The primary goal is identifying where None values are returned unexpectedly
4. **Minimal dependencies**: Scripts are designed to work with minimal external dependencies for maximum isolation

## 🔄 Next Steps

After running these scripts:

1. **Identify the failing component** from the test results
2. **Focus debugging efforts** on the specific component that returns None
3. **Use the detailed logs** to pinpoint the exact line/function causing issues
4. **Apply targeted fixes** to the identified component
5. **Re-run scripts** to verify fixes work in isolation before testing full system