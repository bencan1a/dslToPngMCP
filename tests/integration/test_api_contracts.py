"""
Integration Tests for API Contracts
===================================

Basic integration tests for FastAPI endpoints that actually exist.
Tests request/response validation and API contract compliance.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from src.api.main import create_app
from src.models.schemas import TaskStatus

from tests.utils.data_generators import MockDataGenerator
from tests.utils.helpers import measure_performance


class TestBasicAPIEndpoints:
    """Test basic API endpoints and contracts."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_dsl_request(self):
        """Create sample DSL render request."""
        return {
            "dsl_content": json.dumps({
                "title": "API Test Document",
                "viewport": {"width": 800, "height": 600},
                "elements": [
                    {
                        "type": "text",
                        "content": "Hello from API",
                        "style": {"fontSize": "24px", "color": "#333"}
                    }
                ]
            }),
            "options": {
                "width": 800,
                "height": 600,
                "device_scale_factor": 1.0
            }
        }
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "DSL to PNG MCP Server"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        health_data = response.json()
        assert "status" in health_data
        assert "version" in health_data
        assert health_data["version"] == "1.0.0"
    
    def test_validate_endpoint_success(self, client):
        """Test DSL validation endpoint with valid DSL."""
        valid_dsl = {
            "dsl_content": json.dumps({
                "title": "Valid Test",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "Test"}]
            })
        }
        
        with patch('src.core.dsl.parser.validate_dsl_syntax', return_value=True):
            with patch('src.core.dsl.parser.parse_dsl') as mock_parse:
                mock_parse.return_value = Mock(success=True, errors=[])
                
                response = client.post("/validate", json=valid_dsl)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["valid"] is True
                assert len(data["errors"]) == 0
    
    def test_validate_endpoint_invalid_dsl(self, client):
        """Test DSL validation endpoint with invalid DSL."""
        invalid_dsl = {
            "dsl_content": "invalid json syntax"
        }
        
        with patch('src.core.dsl.parser.validate_dsl_syntax', return_value=False):
            response = client.post("/validate", json=invalid_dsl)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is False
            assert len(data["errors"]) > 0
    
    def test_render_endpoint_success(self, client, sample_dsl_request):
        """Test synchronous render endpoint with valid request."""
        with patch('src.core.dsl.parser.parse_dsl') as mock_parse:
            with patch('src.core.rendering.html_generator.generate_html') as mock_html:
                with patch('src.core.rendering.png_generator.generate_png_from_html') as mock_png:
                    
                    # Mock successful parsing
                    mock_parse.return_value = Mock(success=True, document=Mock())
                    
                    # Mock HTML generation
                    mock_html.return_value = "<html>test</html>"
                    
                    # Mock PNG generation
                    mock_result = MockDataGenerator.generate_png_result()
                    mock_png.return_value = mock_result
                    
                    response = client.post("/render", json=sample_dsl_request)
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["success"] is True
                    assert data["png_result"] is not None
                    assert data["processing_time"] > 0
    
    def test_render_endpoint_invalid_dsl(self, client):
        """Test render endpoint with invalid DSL."""
        invalid_request = {
            "dsl_content": "invalid json",
            "options": {"width": 800, "height": 600}
        }
        
        with patch('src.core.dsl.parser.parse_dsl') as mock_parse:
            mock_parse.return_value = Mock(success=False, errors=["Invalid JSON"])
            
            response = client.post("/render", json=invalid_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "error" in data
    
    def test_render_async_endpoint_success(self, client, sample_dsl_request):
        """Test asynchronous render endpoint."""
        with patch('src.core.queue.tasks.submit_render_task') as mock_submit:
            mock_submit.return_value = "test-task-123"
            
            response = client.post("/render/async", json=sample_dsl_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == "test-task-123"
            assert data["status"] == "pending"
    
    def test_task_status_endpoint_success(self, client):
        """Test task status endpoint."""
        task_id = "test-task-456"
        
        with patch('src.core.queue.tasks.TaskTracker.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "completed",
                "progress": 100,
                "message": "Task completed",
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-01T12:01:00"
            }
            
            with patch('src.core.queue.tasks.get_task_result') as mock_result:
                mock_result.return_value = {"content_hash": "abc123"}
                
                response = client.get(f"/status/{task_id}")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["task_id"] == task_id
                assert data["status"] == "completed"
                assert data["result"]["content_hash"] == "abc123"
    
    def test_task_status_endpoint_not_found(self, client):
        """Test task status endpoint with non-existent task."""
        task_id = "non-existent-task"
        
        with patch('src.core.queue.tasks.TaskTracker.get_task_status') as mock_status:
            mock_status.return_value = None
            
            response = client.get(f"/status/{task_id}")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_cancel_task_endpoint_success(self, client):
        """Test task cancellation endpoint."""
        task_id = "test-task-789"
        
        with patch('src.core.queue.tasks.cancel_task') as mock_cancel:
            mock_cancel.return_value = True
            
            response = client.delete(f"/tasks/{task_id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "cancelled successfully" in data["message"]
    
    def test_cancel_task_endpoint_failure(self, client):
        """Test task cancellation endpoint failure."""
        task_id = "test-task-999"
        
        with patch('src.core.queue.tasks.cancel_task') as mock_cancel:
            mock_cancel.return_value = False
            
            response = client.delete(f"/tasks/{task_id}")
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAPIErrorHandling:
    """Test API error handling and response formatting."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_validation_error_format(self, client):
        """Test validation error response format."""
        invalid_request = {
            "dsl_content": 123,  # Should be string
            "options": {"width": "not a number"}  # Should be number
        }
        
        response = client.post("/render", json=invalid_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data
    
    def test_internal_server_error_handling(self, client):
        """Test internal server error handling."""
        sample_request = {
            "dsl_content": json.dumps({"title": "Error Test", "viewport": {"width": 800, "height": 600}, "elements": []}),
            "options": {"width": 800, "height": 600}
        }
        
        with patch('src.core.dsl.parser.parse_dsl') as mock_parse:
            mock_parse.side_effect = Exception("Internal processing error")
            
            response = client.post("/render", json=sample_request)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            error_data = response.json()
            assert "error" in error_data
    
    def test_not_found_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        error_data = response.json()
        assert "detail" in error_data
    
    def test_method_not_allowed_error_handling(self, client):
        """Test 405 error handling."""
        response = client.patch("/render")  # PATCH not allowed
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestAPIPerformance:
    """Test API performance characteristics."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_api_response_time(self, client):
        """Test API response time performance."""
        with measure_performance() as timer:
            response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        # Health check should be very fast
        assert timer.elapsed_time < 1.0
    
    def test_concurrent_health_checks(self, client):
        """Test concurrent API request handling."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads for concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(code == status.HTTP_200_OK for code in results)
        
        # Should handle concurrent requests efficiently
        assert (end_time - start_time) < 2.0


class TestAPIDocumentation:
    """Test API documentation and OpenAPI compliance."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_openapi_schema_available(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_api_documentation_endpoints(self, client):
        """Test API documentation endpoints."""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
    
    def test_api_schema_validation(self, client):
        """Test API schema validation against OpenAPI spec."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Basic schema structure validation
        assert schema["info"]["title"]
        assert schema["info"]["version"]
        
        # Check that main endpoints are documented
        paths = schema["paths"]
        assert "/render" in paths
        assert "/health" in paths
        assert "/validate" in paths