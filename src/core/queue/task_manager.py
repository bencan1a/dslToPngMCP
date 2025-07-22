"""
Task Manager
============

Manage asynchronous rendering tasks with queue, priority, and status tracking.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import uuid

from src.config.logging import get_logger
from src.models.schemas import DSLRenderRequest, RenderOptions, TaskStatus

logger = get_logger(__name__)


class TaskManager:
    """
    Task manager for handling asynchronous rendering tasks.
    Used by integration tests and queue management.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="task_manager")
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.queue: List[str] = []
    
    async def initialize(self):
        """Initialize the task manager."""
        self.logger.info("Task manager initialized")
    
    async def close(self):
        """Close the task manager."""
        self.logger.info("Task manager closed")
    
    async def submit_task(self, dsl_content: Dict[str, Any], render_options: RenderOptions, priority: int = 1) -> str:
        """
        Submit a new rendering task.
        
        Args:
            dsl_content: DSL document data
            render_options: Rendering options
            priority: Task priority
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task_data = {
            "task_id": task_id,
            "dsl_content": dsl_content,
            "render_options": render_options,
            "priority": priority,
            "status": TaskStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.tasks[task_id] = task_data
        self.queue.append(task_id)
        
        self.logger.info("Task submitted", task_id=task_id, priority=priority)
        return task_id
    
    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Get the next task from the queue.
        
        Returns:
            Task data or None if queue is empty
        """
        if not self.queue:
            return None
        
        task_id = self.queue.pop(0)
        task_data = self.tasks.get(task_id)
        
        if task_data:
            task_data["status"] = TaskStatus.PROCESSING
            task_data["updated_at"] = datetime.utcnow().isoformat()
        
        return task_data
    
    async def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[Dict[str, Any]] = None):
        """
        Update task status.
        
        Args:
            task_id: Task identifier
            status: New task status
            result: Task result data
        """
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            self.tasks[task_id]["updated_at"] = datetime.utcnow().isoformat()
            
            if result:
                self.tasks[task_id]["result"] = result
            
            if status == TaskStatus.COMPLETED:
                self.tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task data or None if not found
        """
        return self.tasks.get(task_id)