"""
FastAPI REST Endpoints
======================

REST API endpoints for HTTP access to DSL rendering functionality.

Endpoints:
- POST /render: Synchronous DSL to PNG conversion
- POST /render/async: Asynchronous DSL to PNG conversion with job tracking
- GET /status/{job_id}: Get rendering job status
- GET /health: Health check endpoint
"""