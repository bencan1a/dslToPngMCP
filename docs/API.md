# API Documentation

Complete API reference for the DSL to PNG MCP Server, covering both Model Context Protocol (MCP) tools and REST endpoints.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [MCP Protocol Tools](#mcp-protocol-tools)
- [REST API Endpoints](#rest-api-endpoints)
- [Request/Response Schemas](#requestresponse-schemas)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

---

## Overview

The DSL to PNG MCP Server provides two primary interfaces:

1. **MCP Protocol Tools**: For AI agents and MCP-compatible clients
2. **REST API**: For traditional HTTP-based integrations

Both interfaces provide the same core functionality: converting Domain Specific Language (DSL) definitions into high-quality PNG images.

### Base URLs

- **FastAPI Server**: `http://localhost:8000` (development) | `https://your-domain.com` (production)
- **MCP Server**: Via stdio transport or TCP on port 3001

---

## Authentication

### API Key Authentication (Optional)

When `API_KEY` environment variable is set, include the API key in requests:

**Header:**
```http
Authorization: Bearer YOUR_API_KEY
```

**Query Parameter:**
```http
GET /health?api_key=YOUR_API_KEY
```

### CORS Configuration

The server supports CORS with configurable allowed origins via the `ALLOWED_HOSTS` environment variable.

---

## MCP Protocol Tools

The MCP server implements three core tools for DSL to PNG conversion.

### Tool: `render_ui_mockup`

Convert DSL (Domain Specific Language) to PNG image mockup.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "dsl_content": {
      "type": "string",
      "description": "DSL content defining the UI mockup (JSON or YAML format)"
    },
    "width": {
      "type": "integer",
      "description": "Render width in pixels",
      "default": 800,
      "minimum": 100,
      "maximum": 2000
    },
    "height": {
      "type": "integer",
      "description": "Render height in pixels", 
      "default": 600,
      "minimum": 100,
      "maximum": 2000
    },
    "async_mode": {
      "type": "boolean",
      "description": "Whether to process asynchronously",
      "default": false
    },
    "options": {
      "type": "object",
      "description": "Additional rendering options",
      "properties": {
        "device_scale_factor": {"type": "number", "default": 1.0},
        "wait_for_load": {"type": "boolean", "default": true},
        "optimize_png": {"type": "boolean", "default": true},
        "transparent_background": {"type": "boolean", "default": false}
      }
    }
  },
  "required": ["dsl_content"]
}
```

**Response (Sync Mode):**
```json
{
  "success": true,
  "png_result": {
    "base64_data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "width": 800,
    "height": 600,
    "file_size": 45231,
    "content_hash": "sha256:abc123...",
    "metadata": {
      "render_type": "synchronous_mcp",
      "parsing_time": 0.023,
      "generation_time": 1.45
    }
  },
  "message": "Synchronous rendering completed successfully"
}
```

**Response (Async Mode):**
```json
{
  "success": true,
  "async": true,
  "task_id": "task_12345",
  "message": "Rendering task submitted successfully",
  "status_check_tool": "get_render_status"
}
```

### Tool: `validate_dsl`

Validate DSL syntax and structure without rendering.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "dsl_content": {
      "type": "string",
      "description": "DSL content to validate"
    },
    "strict": {
      "type": "boolean",
      "description": "Enable strict validation mode",
      "default": false
    }
  },
  "required": ["dsl_content"]
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Large canvas size (1920x1080) may impact performance"],
  "suggestions": []
}
```

### Tool: `get_render_status`

Check the status of an asynchronous rendering job.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Task identifier from async render request"
    }
  },
  "required": ["task_id"]
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task_12345",
  "status": "completed",
  "progress": 100,
  "message": "Rendering completed successfully",
  "updated_at": "2024-01-20T10:30:00Z",
  "result": {
    "png_result": {
      "base64_data": "iVBORw0KGgoAAAANSUhEUgAA...",
      "width": 800,
      "height": 600,
      "file_size": 45231,
      "metadata": {}
    }
  }
}
```

---

## REST API Endpoints

### Health Check

**GET** `/health`

Get application health status including service dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "version": "1.0.0",
  "database": true,
  "redis": true,
  "browser_pool": true,
  "celery": true,
  "active_tasks": 3,
  "queue_size": 5
}
```

### DSL Validation

**POST** `/validate`

Validate DSL content without rendering.

**Request Body:**
```json
{
  "dsl_content": "{\n  \"width\": 400,\n  \"height\": 300,\n  \"elements\": [...]\n}",
  "strict": false
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "suggestions": []
}
```

### Synchronous Rendering

**POST** `/render`

Render DSL to PNG synchronously (recommended for simple DSL documents).

**Request Body:**
```json
{
  "dsl_content": "{\n  \"width\": 800,\n  \"height\": 600,\n  \"elements\": [...]\n}",
  "options": {
    "width": 800,
    "height": 600,
    "device_scale_factor": 1.0,
    "wait_for_load": true,
    "optimize_png": true,
    "transparent_background": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "png_result": {
    "png_data": "binary_data_here",
    "base64_data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "width": 800,
    "height": 600,
    "file_size": 45231,
    "metadata": {
      "content_hash": "sha256:abc123...",
      "render_type": "synchronous"
    }
  },
  "error": null,
  "processing_time": 2.34
}
```

### Asynchronous Rendering

**POST** `/render/async`

Submit DSL for asynchronous rendering (recommended for complex DSL documents).

**Request Body:**
```json
{
  "dsl_content": "{\n  \"width\": 1200,\n  \"height\": 800,\n  \"elements\": [...]\n}",
  "options": {
    "width": 1200,
    "height": 800,
    "device_scale_factor": 2.0,
    "wait_for_load": true,
    "optimize_png": true
  },
  "callback_url": "https://your-app.com/webhook/render-complete"
}
```

**Response:**
```json
{
  "task_id": "task_67890",
  "status": "pending",
  "estimated_completion": "2024-01-20T10:35:00Z"
}
```

### Task Status

**GET** `/status/{task_id}`

Get the status of an asynchronous rendering task.

**Response:**
```json
{
  "task_id": "task_67890",
  "status": "processing",
  "progress": 65,
  "message": "Generating PNG from HTML",
  "result": null,
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-01-20T10:32:15Z"
}
```

### Task Cancellation

**DELETE** `/tasks/{task_id}`

Cancel a running rendering task.

**Response:**
```json
{
  "success": true,
  "message": "Task cancelled successfully"
}
```

---

## Request/Response Schemas

### DSL Content Format

DSL content can be provided in JSON or YAML format:

**JSON Example:**
```json
{
  "title": "My UI Mockup",
  "width": 800,
  "height": 600,
  "elements": [
    {
      "type": "button",
      "layout": {"x": 100, "y": 50, "width": 120, "height": 40},
      "style": {"background": "#007bff", "color": "white"},
      "label": "Click me"
    }
  ]
}
```

**YAML Example:**
```yaml
title: "My UI Mockup"
width: 800
height: 600
elements:
  - type: "button"
    layout:
      x: 100
      y: 50
      width: 120
      height: 40
    style:
      background: "#007bff"
      color: "white"
    label: "Click me"
```

### Render Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `width` | integer | 800 | Render width in pixels (100-4000) |
| `height` | integer | 600 | Render height in pixels (100-4000) |
| `device_scale_factor` | number | 1.0 | Device pixel ratio (0.5-3.0) |
| `wait_for_load` | boolean | true | Wait for page load completion |
| `optimize_png` | boolean | true | Optimize PNG file size |
| `transparent_background` | boolean | false | Use transparent background |
| `timeout` | integer | 30 | Render timeout in seconds |

### Task Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task queued for processing |
| `processing` | Task currently being executed |
| `completed` | Task completed successfully |
| `failed` | Task failed with error |
| `cancelled` | Task was cancelled |

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid API key |
| 404 | Not Found - Task/resource not found |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Health check failed |

### Error Response Format

```json
{
  "error": "DSL parsing failed: Invalid JSON syntax at line 5",
  "error_code": "DSL_PARSE_ERROR",
  "details": {
    "line": 5,
    "column": 12,
    "suggestion": "Check for missing comma"
  },
  "timestamp": "2024-01-20T10:30:00Z",
  "request_id": "req_12345"
}
```

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `DSL_PARSE_ERROR` | DSL syntax error | Check JSON/YAML formatting |
| `DSL_VALIDATION_ERROR` | DSL structure invalid | Review DSL schema requirements |
| `RENDER_TIMEOUT` | Rendering took too long | Simplify DSL or increase timeout |
| `BROWSER_ERROR` | Browser automation failed | Check browser pool status |
| `STORAGE_ERROR` | File storage failed | Check disk space and permissions |

---

## Rate Limiting

### Default Limits

- **Synchronous rendering**: 10 requests/minute per IP
- **Asynchronous rendering**: 20 requests/minute per IP  
- **Validation**: 100 requests/minute per IP
- **Status checks**: 200 requests/minute per IP

### Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642680600
```

### Rate Limit Response

When rate limit is exceeded:

```json
{
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 10,
    "window": "1 minute",
    "retry_after": 45
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

---

## Examples

### Complete MCP Tool Usage

```python
# Using MCP client to render DSL
import mcp

client = mcp.Client()
await client.connect("stdio", command=["python", "-m", "src.mcp_server.server"])

# Simple button render
result = await client.call_tool("render_ui_mockup", {
    "dsl_content": """{
        "width": 400,
        "height": 200,
        "elements": [{
            "type": "button",
            "layout": {"x": 150, "y": 80, "width": 100, "height": 40},
            "style": {"background": "#007bff", "color": "white"},
            "label": "Click Me!"
        }]
    }""",
    "width": 400,
    "height": 200
})

print(f"Success: {result['success']}")
print(f"PNG size: {result['png_result']['file_size']} bytes")
```

### REST API Usage

```python
import requests
import base64

# Validate DSL
response = requests.post("http://localhost:8000/validate", json={
    "dsl_content": """{
        "width": 800,
        "height": 600,
        "elements": [{
            "type": "text",
            "text": "Hello World",
            "layout": {"x": 100, "y": 100, "width": 200, "height": 50}
        }]
    }"""
})

validation = response.json()
if validation["valid"]:
    # Render synchronously
    response = requests.post("http://localhost:8000/render", json={
        "dsl_content": validation_request["dsl_content"],
        "options": {
            "width": 800,
            "height": 600,
            "optimize_png": True
        }
    })
    
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            # Save PNG
            png_data = base64.b64decode(result["png_result"]["base64_data"])
            with open("output.png", "wb") as f:
                f.write(png_data)
            print(f"PNG saved: {result['png_result']['file_size']} bytes")
```

### Async Rendering with Status Polling

```python
import requests
import time

# Submit async render
response = requests.post("http://localhost:8000/render/async", json={
    "dsl_content": complex_dsl_content,
    "options": {"width": 1200, "height": 800}
})

task_id = response.json()["task_id"]
print(f"Task submitted: {task_id}")

# Poll for completion
while True:
    response = requests.get(f"http://localhost:8000/status/{task_id}")
    status = response.json()
    
    print(f"Status: {status['status']} ({status['progress']}%)")
    
    if status["status"] == "completed":
        png_data = base64.b64decode(status["result"]["png_result"]["base64_data"])
        with open("async_output.png", "wb") as f:
            f.write(png_data)
        break
    elif status["status"] == "failed":
        print(f"Task failed: {status['message']}")
        break
    
    time.sleep(2)
```

### Error Handling Example

```python
import requests
from requests.exceptions import HTTPError

def render_dsl_with_retry(dsl_content, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post("http://localhost:8000/render", 
                json={"dsl_content": dsl_content},
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            if result["success"]:
                return result["png_result"]
            else:
                print(f"Render failed: {result['error']}")
                return None
                
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                retry_after = int(e.response.headers.get("Retry-After", 60))
                print(f"Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            elif e.response.status_code >= 500:  # Server error
                print(f"Server error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            raise
        except requests.exceptions.Timeout:
            print(f"Request timeout (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                continue
            raise
    
    return None
```

---

## Additional Resources

- [DSL Reference](./DSL_REFERENCE.md) - Complete DSL syntax documentation
- [User Guide](./USER_GUIDE.md) - Step-by-step usage instructions
- [Examples](./examples/) - Complete example projects
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions