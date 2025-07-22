"""
Integration Tests for MCP Protocol
==================================

Basic integration tests for the DSL to PNG MCP server implementation.
Tests server instantiation and basic configuration.
"""

import pytest
from src.mcp_server.server import DSLToPNGMCPServer


class TestMCPServerBasics:
    """Test basic MCP server functionality."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance for testing."""
        server = DSLToPNGMCPServer()
        return server
    
    def test_server_initialization(self, mcp_server):
        """Test MCP server initialization."""
        assert mcp_server is not None
        assert hasattr(mcp_server, 'server')
        assert hasattr(mcp_server, 'settings')
        assert hasattr(mcp_server, 'logger')
    
    def test_server_has_mcp_server(self, mcp_server):
        """Test that MCP server has the underlying MCP server."""
        assert mcp_server.server is not None
        assert mcp_server.server.name == "dsl-to-png-mcp"
    
    def test_server_settings_configuration(self, mcp_server):
        """Test server settings configuration."""
        assert mcp_server.settings is not None
        assert hasattr(mcp_server.settings, 'celery_broker_url')
        assert hasattr(mcp_server.settings, 'celery_result_backend')


class TestMCPServerResourceMethods:
    """Test MCP server resource generation methods."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance for testing."""
        server = DSLToPNGMCPServer()
        return server
    
    @pytest.mark.asyncio
    async def test_get_element_types_schema(self, mcp_server):
        """Test element types schema generation."""
        schema_json = await mcp_server._get_element_types_schema()
        assert schema_json is not None
        
        import json
        schema = json.loads(schema_json)
        assert "element_types" in schema
        assert "schema_version" in schema
        assert len(schema["element_types"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_basic_examples(self, mcp_server):
        """Test basic examples generation."""
        examples_json = await mcp_server._get_basic_examples()
        assert examples_json is not None
        
        import json
        examples = json.loads(examples_json)
        assert "simple_button" in examples
        assert "login_form" in examples
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, mcp_server):
        """Test health status generation."""
        health_json = await mcp_server._get_health_status()
        assert health_json is not None
        
        import json
        health = json.loads(health_json)
        assert "status" in health
        assert "timestamp" in health
        assert "services" in health