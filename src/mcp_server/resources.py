"""
MCP Server Resources
====================

Resource implementations for the MCP (Model Context Protocol) server.
Provides access to stored files, task information, and system resources.
"""

from typing import Dict, Any, Optional, Tuple
import json

from src.config.logging import get_logger

logger = get_logger(__name__)


class StorageResource:
    """Resource for accessing stored files."""
    
    def __init__(self):
        self.logger = logger.bind(resource="storage")
    
    async def read(self, uri: str) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Read stored file data.
        
        Args:
            uri: Resource URI (e.g., "storage://files/abc123")
            
        Returns:
            Tuple of (file_data, metadata) or None if not found
        """
        try:
            # Extract content hash from URI
            parts = uri.split("/")
            if len(parts) < 3:
                return None
            
            content_hash = parts[-1]
            
            # Mock file data and metadata
            mock_data = b"mock_png_data_for_" + content_hash.encode()
            mock_metadata = {
                "content_hash": content_hash,
                "file_size": len(mock_data),
                "created_at": "2023-01-01T12:00:00Z",
                "content_type": "image/png"
            }
            
            return mock_data, mock_metadata
            
        except Exception as e:
            self.logger.error("Storage resource read failed", error=str(e), uri=uri)
            return None


class TaskResource:
    """Resource for accessing task information."""
    
    def __init__(self):
        self.logger = logger.bind(resource="task")
    
    async def read(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Read task information.
        
        Args:
            uri: Resource URI (e.g., "tasks://queue/task-123")
            
        Returns:
            Task information or None if not found
        """
        try:
            # Extract task ID from URI
            parts = uri.split("/")
            if len(parts) < 3:
                return None
            
            task_id = parts[-1]
            
            # Mock task information
            task_info = {
                "task_id": task_id,
                "status": "completed",
                "created_at": "2023-01-01T12:00:00Z",
                "completed_at": "2023-01-01T12:01:00Z",
                "result": {"content_hash": "def456", "file_size": 1024},
                "processing_time": 60.0
            }
            
            return task_info
            
        except Exception as e:
            self.logger.error("Task resource read failed", error=str(e), uri=uri)
            return None


# Function versions for direct usage
async def get_stored_file(content_hash: str) -> Optional[Tuple[bytes, Dict[str, Any]]]:
    """
    Get stored file by content hash.
    Used by integration tests and other modules.
    
    Args:
        content_hash: File content hash
        
    Returns:
        Tuple of (file_data, metadata) or None if not found
    """
    resource = StorageResource()
    return await resource.read(f"storage://files/{content_hash}")


async def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get task information by task ID.
    Used by integration tests and other modules.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task information or None if not found
    """
    resource = TaskResource()
    return await resource.read(f"tasks://queue/{task_id}")