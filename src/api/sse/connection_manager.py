"""
SSE Connection Manager
=====================

Manages Server-Sent Events connections and event delivery.
Handles connection lifecycle, event queuing, and delivery.
"""

from typing import Dict, List, Optional, Any, AsyncIterator
import asyncio
import uuid
from datetime import datetime, timezone
import json
import time
from contextlib import asynccontextmanager

from fastapi import Request

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.config.database import get_redis_client  # type: ignore

from .models import SSEConnectionMetadata, SSEConnectionStatus
from .events import (
    SSEEvent,
    SSEEventType,
    create_connection_opened_event,
    create_connection_closed_event,
    create_heartbeat_event,
)

logger = get_logger(__name__)


def _safe_decode(data: Any) -> str:
    """Safely decode Redis data that might be bytes or str."""
    if isinstance(data, bytes):
        return data.decode()
    return str(data)


class SSEConnectionManager:
    """
    Manages SSE connections and event delivery.

    Handles:
    - Connection lifecycle (open, heartbeat, close)
    - Event queuing and delivery
    - Connection cleanup and monitoring
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        # Use Redis for shared state across workers
        self.redis: Any = get_redis_client()  # Type annotation to resolve Redis client issues
        self.redis_connections_key = "sse:connections"
        self.redis_client_map_key = "sse:client_map"
        self.redis_buffers_key = "sse:buffers"

        # Local cache for active connection queues (worker-specific)
        self.local_queues: Dict[str, asyncio.Queue[Optional[str]]] = {}

        # Connection and event buffer management
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.event_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.client_id_map: Dict[str, str] = {}

        self.logger: Any = logger.bind(component="sse_manager")  # structlog.BoundLoggerBase
        self.settings = get_settings()
        self.heartbeat_task: Optional[asyncio.Task[None]] = None
        self.cleanup_task: Optional[asyncio.Task[None]] = None
        self.redis_pubsub_task: Optional[asyncio.Task[Any]] = None
        self.redis_channel = "sse_events"
        self.buffer_size = self.settings.sse_event_buffer_size
        self.connection_timeout = self.settings.sse_connection_timeout_seconds
        self.heartbeat_interval = self.settings.sse_heartbeat_interval_seconds

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """Start background tasks for connection management."""
        import os

        worker_id = os.getpid()

        self.logger.info(
            f"WORKER {worker_id}: Starting background tasks for SSE connection manager"
        )

        try:
            if not self.heartbeat_task or self.heartbeat_task.done():
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self.logger.info(f"WORKER {worker_id}: ✅ Heartbeat task started successfully")

            if not self.cleanup_task or self.cleanup_task.done():
                self.cleanup_task = asyncio.create_task(self._cleanup_loop())
                self.logger.info(f"WORKER {worker_id}: ✅ Cleanup task started successfully")

            if not self.redis_pubsub_task or self.redis_pubsub_task.done():
                self.logger.info(f"WORKER {worker_id}: 🔄 About to start Redis pub/sub task...")
                self.redis_pubsub_task = asyncio.create_task(self._redis_pubsub_loop())
                self.logger.info(f"WORKER {worker_id}: ✅ Redis pub/sub task started successfully")
        except Exception as e:
            self.logger.error(
                f"WORKER {worker_id}: 🚨 CRITICAL ERROR starting background tasks",
                error_type=type(e).__name__,
                error_message=str(e),
                error_repr=repr(e),
            )
            raise

    async def create_connection(
        self, request: Request, client_id: Optional[str] = None, last_event_id: Optional[str] = None
    ) -> str:
        """
        Create a new SSE connection.

        Args:
            request: FastAPI request
            client_id: Optional client identifier for reconnection
            last_event_id: Optional last event ID for resuming

        Returns:
            Connection ID
        """
        # Generate connection ID
        connection_id = str(uuid.uuid4())

        # Log worker process info for diagnosis
        import os

        worker_id = os.getpid()
        self.logger.info(f"WORKER {worker_id}: Creating connection {connection_id}")

        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        api_key = request.headers.get("x-api-key")
        api_key_hash = self._hash_api_key(api_key) if api_key else None

        # Create connection metadata
        metadata = SSEConnectionMetadata(
            connection_id=connection_id,
            client_ip=client_ip,
            user_agent=user_agent,
            api_key_hash=api_key_hash,
            status=SSEConnectionStatus.CONNECTING,
            connected_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            metadata={"client_id": client_id, "last_event_id": last_event_id},
        )

        # Store connection in Redis (serialize datetime objects)
        metadata_dict = metadata.model_dump()
        # Convert datetime objects to ISO strings for JSON serialization
        if "connected_at" in metadata_dict:
            metadata_dict["connected_at"] = metadata_dict["connected_at"].isoformat()
        if "last_heartbeat" in metadata_dict:
            metadata_dict["last_heartbeat"] = metadata_dict["last_heartbeat"].isoformat()

        connection_data = {
            "metadata": metadata_dict,
            "last_activity": time.time(),
            "worker_pid": os.getpid(),  # Track which worker owns this connection
        }

        # 🔍 REDIS DIAGNOSTIC: Log connection creation before Redis hset
        self.logger.info(
            "🔍 CONNECTION CREATION REDIS DIAGNOSTIC: About to store new connection in Redis",
            connection_id=connection_id,
            worker_id=worker_id,
            redis_key=self.redis_connections_key,
            connection_data_keys=list(connection_data.keys()),
            connection_data_types={k: type(v).__name__ for k, v in connection_data.items()},
            metadata_dict_keys=list(metadata_dict.keys()),
            metadata_dict_types={k: type(v).__name__ for k, v in metadata_dict.items()},
        )

        # Test JSON serialization before Redis operation
        try:
            json_test = json.dumps(connection_data)
            self.logger.info(
                "🔍 CONNECTION CREATION JSON SUCCESS: Connection data serializes correctly",
                connection_id=connection_id,
                json_length=len(json_test),
            )
        except Exception as json_error:
            self.logger.error(
                "🚨 CONNECTION CREATION JSON ERROR: Connection data cannot be serialized",
                connection_id=connection_id,
                json_error_type=type(json_error).__name__,
                json_error_message=str(json_error),
                connection_data_causing_error=connection_data,
            )
            raise

        # Wrap Redis hset in try-catch
        try:
            self.logger.info(
                "🔍 REDIS HSET: About to execute hset for connection creation",
                connection_id=connection_id,
                redis_key=self.redis_connections_key,
            )

            await self.redis.hset(
                self.redis_connections_key, connection_id, json.dumps(connection_data)
            )

            self.logger.info(
                "🔍 REDIS HSET SUCCESS: Connection creation hset completed successfully",
                connection_id=connection_id,
                worker_id=worker_id,
            )

        except Exception as redis_error:
            self.logger.error(
                "🚨 REDIS CONNECTION CREATION ERROR: Failed to store new connection - EXACT ERROR LOCATION",
                connection_id=connection_id,
                worker_id=worker_id,
                redis_key=self.redis_connections_key,
                redis_error_type=type(redis_error).__name__,
                redis_error_module=getattr(type(redis_error), "__module__", "unknown"),
                redis_error_message=str(redis_error),
                redis_error_repr=repr(redis_error),
                connection_data_causing_error=connection_data,
                problematic_creation_values={
                    k: {"value": v, "type": type(v).__name__} for k, v in connection_data.items()
                },
            )
            raise

        # Create local queue for this connection
        self.local_queues[connection_id] = asyncio.Queue()

        # Initialize event buffer in Redis
        buffer_key = f"{self.redis_buffers_key}:{connection_id}"
        await self.redis.delete(buffer_key)  # Clear any existing buffer

        # Map client ID if provided
        if client_id:
            # Check for existing connection with this client ID
            old_connection_id = await self.redis.hget(self.redis_client_map_key, client_id)
            if old_connection_id and _safe_decode(old_connection_id) != connection_id:
                # Close old connection if it exists
                if await self._connection_exists(_safe_decode(old_connection_id)):
                    await self.close_connection(_safe_decode(old_connection_id), "reconnected")

            # Update client ID mapping
            await self.redis.hset(self.redis_client_map_key, client_id, connection_id)

        # Update connection status
        metadata.status = SSEConnectionStatus.CONNECTED

        # Send connection opened event using the serialized metadata_dict
        opened_event = create_connection_opened_event(connection_id, metadata_dict)
        await self.send_to_connection(connection_id, opened_event)

        # If last_event_id provided, replay missed events
        if last_event_id:
            await self._replay_missed_events(connection_id, last_event_id)

        # Get total connection count from Redis
        total_connections = await self.redis.hlen(self.redis_connections_key)

        self.logger.info(
            f"WORKER {worker_id}: SSE connection created successfully",
            connection_id=connection_id,
            client_ip=client_ip,
            client_id=client_id,
            total_connections=total_connections,
        )

        return connection_id

    async def _connection_exists(self, connection_id: str) -> bool:
        """Check if connection exists in Redis."""
        return await self.redis.hexists(self.redis_connections_key, connection_id)

    async def _get_connection_data(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection data from Redis."""
        data = await self.redis.hget(self.redis_connections_key, connection_id)
        if data:
            try:
                decoded_data = _safe_decode(data)
                if not decoded_data or decoded_data.strip() == "":
                    self.logger.warning(f"Empty connection data for {connection_id}")
                    return None
                return json.loads(decoded_data)
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"Failed to parse connection data for {connection_id}: {e}, data: {data}"
                )
                return None
            except Exception as e:
                self.logger.error(
                    f"Unexpected error parsing connection data for {connection_id}: {e}"
                )
                return None
        return None

    async def _update_connection_activity(self, connection_id: str) -> None:
        """Update connection last activity in Redis."""
        import os

        worker_id = os.getpid()
        self.logger.info(f"WORKER {worker_id}: Updating activity for connection {connection_id}")

        connection_data = await self._get_connection_data(connection_id)
        if connection_data:
            connection_data["last_activity"] = time.time()

            # 🔍 REDIS DIAGNOSTIC: Log connection activity update before Redis hset
            self.logger.info(
                "🔍 CONNECTION ACTIVITY REDIS DIAGNOSTIC: About to update connection activity in Redis",
                connection_id=connection_id,
                worker_id=worker_id,
                redis_key=self.redis_connections_key,
                connection_data_keys=list(connection_data.keys()) if connection_data else [],
                connection_data_types=(
                    {k: type(v).__name__ for k, v in connection_data.items()}
                    if connection_data
                    else {}
                ),
                none_values_in_connection_data=(
                    [k for k, v in connection_data.items() if v is None] if connection_data else []
                ),
                last_activity_value=connection_data.get("last_activity"),
                last_activity_type=type(connection_data.get("last_activity")).__name__,
            )

            # Test JSON serialization of connection_data
            try:
                json_test = json.dumps(connection_data)
                self.logger.info(
                    "🔍 CONNECTION JSON SUCCESS: Connection data serializes correctly",
                    connection_id=connection_id,
                    json_length=len(json_test),
                )
            except Exception as json_error:
                self.logger.error(
                    "🚨 CONNECTION JSON ERROR: Connection data cannot be serialized",
                    connection_id=connection_id,
                    json_error_type=type(json_error).__name__,
                    json_error_message=str(json_error),
                    connection_data_causing_error=connection_data,
                )
                return

            # Wrap Redis hset in try-catch
            try:
                self.logger.info(
                    "🔍 REDIS HSET: About to execute hset for connection activity",
                    connection_id=connection_id,
                    redis_key=self.redis_connections_key,
                )

                await self.redis.hset(
                    self.redis_connections_key, connection_id, json.dumps(connection_data)
                )

                self.logger.info(
                    "🔍 REDIS HSET SUCCESS: Connection activity updated successfully",
                    connection_id=connection_id,
                    worker_id=worker_id,
                )

            except Exception as redis_error:
                self.logger.error(
                    "🚨 REDIS CONNECTION ACTIVITY ERROR: Failed to update connection activity - EXACT ERROR LOCATION",
                    connection_id=connection_id,
                    worker_id=worker_id,
                    redis_key=self.redis_connections_key,
                    redis_error_type=type(redis_error).__name__,
                    redis_error_module=getattr(type(redis_error), "__module__", "unknown"),
                    redis_error_message=str(redis_error),
                    redis_error_repr=repr(redis_error),
                    connection_data_causing_error=connection_data,
                    problematic_connection_values=(
                        {
                            k: {"value": v, "type": type(v).__name__, "is_none": v is None}
                            for k, v in connection_data.items()
                        }
                        if connection_data
                        else {}
                    ),
                )
                return

            self.logger.info(f"WORKER {worker_id}: Updated activity for connection {connection_id}")
        else:
            self.logger.warning(
                f"WORKER {worker_id}: Connection {connection_id} not found when updating activity"
            )

    def _hash_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Hash API key for secure storage."""
        if not api_key:
            return None

        import hashlib

        # Create a simple hash of the API key
        # In a production system, you would use a more secure method
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def _replay_missed_events(self, connection_id: str, last_event_id: str) -> None:
        """
        Replay missed events for a reconnecting client.

        Args:
            connection_id: Connection ID
            last_event_id: Last event ID received by client
        """
        # Get buffer key for this connection
        buffer_key = f"{self.redis_buffers_key}:{connection_id}"

        # Get all events from buffer
        events_data = await self.redis.lrange(buffer_key, 0, -1)
        if not events_data:
            return

        # Parse events and find those after last_event_id
        missed_events: List[Dict[str, Any]] = []
        found_last_event = False

        for event_data_bytes in events_data:
            try:
                event_data = json.loads(_safe_decode(event_data_bytes))
                event_id = event_data.get("id")

                # If we found the last event, add all subsequent events
                if found_last_event:
                    missed_events.append(event_data)
                elif event_id == last_event_id:
                    found_last_event = True
            except Exception as e:
                self.logger.error(
                    f"Error parsing event data during replay: {e}",
                    connection_id=connection_id,
                    event_data=_safe_decode(event_data_bytes),
                )

        # Send missed events in chronological order (oldest first)
        missed_events.reverse()
        for event_data in missed_events:
            try:
                # Send raw SSE data directly to queue
                if connection_id in self.local_queues:
                    raw_sse = event_data.get("raw")
                    if raw_sse:
                        await self.local_queues[connection_id].put(raw_sse)
            except Exception as e:
                self.logger.error(
                    f"Error replaying event: {e}",
                    connection_id=connection_id,
                    event_id=event_data.get("id"),
                )

    async def close_connection(self, connection_id: str, reason: str = "closed") -> None:
        """
        Close an SSE connection.

        Args:
            connection_id: Connection ID to close
            reason: Reason for closing
        """
        connection_data = await self._get_connection_data(connection_id)
        if connection_data:
            # Send connection closed event
            closed_event = create_connection_closed_event(connection_id, reason)
            try:
                await self.send_to_connection(connection_id, closed_event)
            except Exception as e:
                # Ignore errors when sending to already closed connection
                import os

                worker_id = os.getpid()
                self.logger.error(
                    f"WORKER {worker_id}: Error sending close event to connection {connection_id}",
                    error=str(e),
                )

            # Remove client ID mapping if exists
            metadata = connection_data.get("metadata", {})
            client_id = metadata.get("metadata", {}).get("client_id")
            if client_id:
                current_connection = await self.redis.hget(self.redis_client_map_key, client_id)
                if current_connection and _safe_decode(current_connection) == connection_id:
                    await self.redis.hdel(self.redis_client_map_key, client_id)

            # Clean up local queue
            if connection_id in self.local_queues:
                queue = self.local_queues[connection_id]
                await queue.put(None)  # Signal to stop
                del self.local_queues[connection_id]

            # Remove connection from Redis
            await self.redis.hdel(self.redis_connections_key, connection_id)

            # Keep event buffer for potential reconnection (will be cleaned up later)

            self.logger.info("SSE connection closed", connection_id=connection_id, reason=reason)

    async def send_to_connection(self, connection_id: str, event: SSEEvent) -> bool:
        """
        Send event to a specific connection.

        Args:
            connection_id: Target connection ID
            event: SSE event to send

        Returns:
            True if sent successfully
        """
        # Check if connection exists in Redis
        if not await self._connection_exists(connection_id):
            self.logger.warning(
                "Attempted to send to non-existent connection", connection_id=connection_id
            )
            return False

        # Update last activity in Redis
        await self._update_connection_activity(connection_id)

        # Add to event buffer in Redis
        event_data = {
            "id": event.event_id,
            "type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "raw": event.format_sse(),
        }

        # 🔍 REDIS DIAGNOSTIC: Log event data before Redis operations
        self.logger.info(
            "🔍 SSE EVENT REDIS DIAGNOSTIC: About to store event in Redis buffer",
            connection_id=connection_id,
            buffer_key=f"{self.redis_buffers_key}:{connection_id}",
            event_id=event.event_id,
            event_type=event.event_type.value,
            event_data_keys=list(event_data.keys()),
            event_data_types={k: type(v).__name__ for k, v in event_data.items()},
            event_data_structure={
                "id_value": event_data.get("id"),
                "id_type": type(event_data.get("id")).__name__,
                "type_value": event_data.get("type"),
                "type_type": type(event_data.get("type")).__name__,
                "data_value": event_data.get("data"),
                "data_type": type(event_data.get("data")).__name__,
                "timestamp_value": event_data.get("timestamp"),
                "timestamp_type": type(event_data.get("timestamp")).__name__,
                "raw_value": event_data.get("raw"),
                "raw_type": type(event_data.get("raw")).__name__,
            },
            json_dumps_test="attempting_serialization",
        )

        # Test JSON serialization safety
        try:
            json_test = json.dumps(event_data)
            self.logger.info(
                "🔍 JSON SERIALIZATION SUCCESS: Event data serializes correctly",
                connection_id=connection_id,
                json_length=len(json_test),
            )
        except Exception as json_error:
            self.logger.error(
                "🚨 JSON SERIALIZATION ERROR: Event data cannot be serialized",
                connection_id=connection_id,
                json_error_type=type(json_error).__name__,
                json_error_message=str(json_error),
                event_data_causing_error=event_data,
            )
            return False

        # Add to Redis buffer with size limit - wrap in try-catch
        buffer_key = f"{self.redis_buffers_key}:{connection_id}"
        try:
            self.logger.info(
                "🔍 REDIS LPUSH: About to execute lpush operation",
                connection_id=connection_id,
                buffer_key=buffer_key,
                redis_client_type=type(self.redis).__name__,
            )

            await self.redis.lpush(buffer_key, json.dumps(event_data))

            self.logger.info(
                "🔍 REDIS LPUSH SUCCESS: lpush completed successfully",
                connection_id=connection_id,
                buffer_key=buffer_key,
            )

            await self.redis.ltrim(buffer_key, 0, self.buffer_size - 1)

            self.logger.info(
                "🔍 REDIS LTRIM SUCCESS: ltrim completed successfully",
                connection_id=connection_id,
                buffer_key=buffer_key,
                buffer_size=self.buffer_size,
            )

        except Exception as redis_error:
            self.logger.error(
                "🚨 REDIS BUFFER ERROR: Failed to store event in Redis buffer - EXACT ERROR LOCATION",
                connection_id=connection_id,
                buffer_key=buffer_key,
                redis_error_type=type(redis_error).__name__,
                redis_error_module=getattr(type(redis_error), "__module__", "unknown"),
                redis_error_message=str(redis_error),
                redis_error_repr=repr(redis_error),
                event_data_causing_error=event_data,
                problematic_redis_values={
                    k: {"value": v, "type": type(v).__name__} for k, v in event_data.items()
                },
            )
            return False

        # Add to local queue if it exists (connection is on this worker)
        if connection_id in self.local_queues:
            queue = self.local_queues[connection_id]
            await queue.put(event.format_sse())

        return True

    async def broadcast(self, event_type: SSEEventType, data: Dict[str, Any]) -> int:
        """
        Broadcast event to all connections.

        Args:
            event_type: Event type
            data: Event data

        Returns:
            Number of connections that received the event
        """
        sent_count = 0

        # Get all connection IDs from Redis
        connection_ids = await self.redis.hkeys(self.redis_connections_key)

        for connection_id_bytes in connection_ids:
            connection_id = _safe_decode(connection_id_bytes)
            try:
                event = SSEEvent(event_type=event_type, data=data, connection_id=connection_id)
                success = await self.send_to_connection(connection_id, event)
                if success:
                    sent_count += 1
            except Exception as e:
                self.logger.error(
                    "Failed to broadcast to connection", connection_id=connection_id, error=str(e)
                )

        return sent_count

    async def get_connection_stream(self, connection_id: str) -> AsyncIterator[str]:
        """
        Get event stream for a connection.

        Args:
            connection_id: Connection ID

        Yields:
            SSE formatted events
        """
        # Check if connection exists in Redis
        if not await self._connection_exists(connection_id):
            self.logger.warning(
                "Attempted to stream non-existent connection", connection_id=connection_id
            )
            return

        # Get local queue (connection must be on this worker to stream)
        if connection_id not in self.local_queues:
            self.logger.warning(
                "Connection exists but not on this worker", connection_id=connection_id
            )
            return

        queue = self.local_queues[connection_id]

        # Stream events
        while True:
            try:
                # Wait for next event
                event = await queue.get()

                # None is a signal to stop
                if event is None:
                    break

                # Update last activity in Redis
                await self._update_connection_activity(connection_id)

                # Yield event
                yield event

                # Mark as done
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Error in connection stream", connection_id=connection_id, error=str(e)
                )
                break

    @asynccontextmanager
    async def connection_stream(self, connection_id: str) -> AsyncIterator[AsyncIterator[str]]:
        """
        Context manager for connection stream.

        Args:
            connection_id: Connection ID

        Yields:
            AsyncIterator of SSE events
        """
        try:
            yield self.get_connection_stream(connection_id)
        finally:
            # Close connection when context exits
            await self.close_connection(connection_id, "stream_ended")

    async def _heartbeat_loop(self) -> None:
        """Background task to send heartbeats to all connections."""
        import os

        worker_id = os.getpid()
        self.logger.info(f"WORKER {worker_id}: Starting heartbeat loop")

        while True:
            try:
                # Wait for heartbeat interval
                await asyncio.sleep(self.heartbeat_interval)

                self.logger.info(
                    f"WORKER {worker_id}: Running heartbeat loop - checking Redis connections"
                )

                # Get all connection IDs from Redis instead of self.connections
                connection_id_bytes = await self.redis.hkeys(self.redis_connections_key)
                connection_ids = [_safe_decode(cid) for cid in connection_id_bytes]

                self.logger.info(
                    f"WORKER {worker_id}: Found {len(connection_ids)} connections in Redis for heartbeat"
                )

                # Send heartbeats
                for connection_id in connection_ids:
                    try:
                        # Get connection data from Redis
                        connection_data = await self._get_connection_data(connection_id)
                        if not connection_data:
                            self.logger.warning(
                                f"WORKER {worker_id}: Connection {connection_id} not found in Redis during heartbeat"
                            )
                            continue

                        # Calculate connection age using Redis data
                        metadata_dict = connection_data.get("metadata", {})
                        connected_at_str = metadata_dict.get("connected_at")
                        if connected_at_str:
                            # Parse ISO datetime string back to datetime object
                            from datetime import datetime as dt

                            connected_at = dt.fromisoformat(connected_at_str.replace("Z", "+00:00"))
                            connection_age = (
                                datetime.now(timezone.utc) - connected_at
                            ).total_seconds()
                        else:
                            connection_age = 0

                        # Send heartbeat
                        heartbeat_event = create_heartbeat_event(connection_id, connection_age)
                        await self.send_to_connection(connection_id, heartbeat_event)

                        # Update last heartbeat in Redis
                        metadata_dict["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                        connection_data["metadata"] = metadata_dict
                        await self.redis.hset(
                            self.redis_connections_key, connection_id, json.dumps(connection_data)
                        )

                        self.logger.info(
                            f"WORKER {worker_id}: Sent heartbeat to connection {connection_id}"
                        )
                    except Exception as e:
                        self.logger.error(
                            "Failed to send heartbeat", connection_id=connection_id, error=str(e)
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in heartbeat loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying

    async def _redis_pubsub_loop(self) -> None:
        """Background task to listen for Redis pub/sub messages and forward them to connections."""
        import os

        worker_id = os.getpid()

        try:
            self.logger.info(f"WORKER {worker_id}: 🚀 STARTING Redis pub/sub loop - ENTRY POINT")

            # Test Redis client availability before starting loop
            try:
                await self.redis.ping()
                self.logger.info(
                    f"WORKER {worker_id}: ✅ Redis client ping successful before pub/sub loop"
                )
            except Exception as ping_error:
                self.logger.error(
                    f"WORKER {worker_id}: 🚨 CRITICAL: Redis ping failed before pub/sub loop",
                    error_type=type(ping_error).__name__,
                    error_message=str(ping_error),
                    error_repr=repr(ping_error),
                )
                raise

            self.logger.info(f"WORKER {worker_id}: 🔄 About to enter Redis pub/sub main loop...")

            while True:
                try:
                    self.logger.info(
                        f"WORKER {worker_id}: 🔄 Creating new Redis pubsub connection..."
                    )

                    # Get Redis pubsub connection
                    pubsub = self.redis.pubsub()
                    self.logger.info(
                        f"WORKER {worker_id}: ✅ Redis pubsub object created successfully"
                    )

                    await pubsub.subscribe(self.redis_channel)
                    self.logger.info(
                        f"WORKER {worker_id}: ✅ Successfully subscribed to Redis channel: {self.redis_channel}"
                    )

                    # Listen for messages
                    self.logger.info(
                        f"WORKER {worker_id}: 🎧 Starting to listen for Redis pub/sub messages..."
                    )
                    async for message in pubsub.listen():
                        try:
                            # Skip subscription confirmation messages
                            message_type = message.get("type")
                            if message_type == "subscribe":
                                self.logger.info(
                                    f"WORKER {worker_id}: 📋 Received subscription confirmation for channel: {self.redis_channel}"
                                )
                                continue

                            # Parse message data
                            message_data = message.get("data")
                            if not message_data:
                                continue

                            # Decode message if it's bytes
                            if isinstance(message_data, bytes):
                                message_data = message_data.decode("utf-8")

                            # 🔍 DIAGNOSTIC: Log incoming Redis message details for format analysis
                            self.logger.info(
                                "🔍 REDIS MESSAGE DIAGNOSTIC: Received message from Redis pubsub",
                                worker_id=worker_id,
                                channel=self.redis_channel,
                                message_type=message_type,
                                message_data_type=type(message_data).__name__,
                                message_data_length=(
                                    len(message_data) if hasattr(message_data, "__len__") else "N/A"
                                ),
                                message_data_preview=(
                                    message_data[:200]
                                    if isinstance(message_data, str)
                                    else str(message_data)[:200]
                                ),
                                is_json_like=(
                                    message_data.strip().startswith("{")
                                    if isinstance(message_data, str)
                                    else False
                                ),
                            )

                            # Parse JSON data
                            try:
                                message_dict = json.loads(message_data)

                                self.logger.info(
                                    "🔍 JSON PARSE SUCCESS: Successfully parsed Redis message as JSON",
                                    worker_id=worker_id,
                                    message_dict_keys=list(message_dict.keys()),
                                    message_dict_types={
                                        k: type(v).__name__ for k, v in message_dict.items()
                                    },
                                )

                                # Extract event details
                                event_type_str = message_dict.get("event_type")
                                if not event_type_str:
                                    self.logger.warning(
                                        "🚨 MISSING EVENT_TYPE: Redis message missing event_type field",
                                        worker_id=worker_id,
                                        message_dict=message_dict,
                                    )
                                    continue

                                # Convert string to enum
                                try:
                                    event_type = SSEEventType(event_type_str)
                                except ValueError:
                                    self.logger.warning(
                                        f"WORKER {worker_id}: Unknown event type: {event_type_str}"
                                    )
                                    continue

                                # Get target connection ID
                                connection_id = message_dict.get("connection_id")
                                if not connection_id:
                                    # Broadcast to all connections if no specific target
                                    data = message_dict.get("data", {})
                                    await self.broadcast(event_type, data)
                                else:
                                    # Send to specific connection
                                    data = message_dict.get("data", {})
                                    event = SSEEvent(
                                        event_type=event_type,
                                        data=data,
                                        connection_id=connection_id,
                                    )
                                    await self.send_to_connection(connection_id, event)

                            except json.JSONDecodeError as e:
                                self.logger.error(
                                    f"WORKER {worker_id}: Failed to parse Redis message: {e}",
                                    message_data=message_data,
                                )
                        except Exception as message_error:
                            self.logger.error(
                                f"WORKER {worker_id}: Error processing Redis message",
                                error_type=type(message_error).__name__,
                                error_message=str(message_error),
                                error_repr=repr(message_error),
                            )
                except asyncio.CancelledError:
                    self.logger.info(f"WORKER {worker_id}: 🛑 Redis pub/sub loop cancelled")
                    break
                except Exception as loop_error:
                    self.logger.error(
                        f"WORKER {worker_id}: 🚨 Redis pub/sub connection error - will retry",
                        error_type=type(loop_error).__name__,
                        error_message=str(loop_error),
                        error_repr=repr(loop_error),
                    )
                    # Wait before reconnecting
                    await asyncio.sleep(5)

        except Exception as critical_error:
            self.logger.error(
                f"WORKER {worker_id}: 🚨 CRITICAL ERROR in Redis pub/sub loop - TASK WILL EXIT",
                error_type=type(critical_error).__name__,
                error_message=str(critical_error),
                error_repr=repr(critical_error),
            )
            raise
        finally:
            self.logger.info(f"WORKER {worker_id}: 🔚 Redis pub/sub loop ended")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up inactive connections."""
        import os

        worker_id = os.getpid()
        self.logger.info(f"WORKER {worker_id}: Starting cleanup loop")

        while True:
            try:
                # Wait for cleanup interval
                await asyncio.sleep(60)  # Check every minute

                now = time.time()

                self.logger.info(
                    f"WORKER {worker_id}: Running cleanup loop - checking Redis connections"
                )

                # Get all connection IDs from Redis
                connection_id_bytes = await self.redis.hkeys(self.redis_connections_key)
                connection_ids = [_safe_decode(cid) for cid in connection_id_bytes]

                self.logger.info(
                    f"WORKER {worker_id}: Found {len(connection_ids)} connections in Redis for cleanup"
                )

                # Check for timed out connections
                for connection_id in connection_ids:
                    try:
                        # Get connection data from Redis
                        connection_data = await self._get_connection_data(connection_id)
                        if not connection_data:
                            self.logger.warning(
                                f"WORKER {worker_id}: Connection {connection_id} not found in Redis during cleanup"
                            )
                            continue

                        last_activity = connection_data.get("last_activity", 0)
                        if now - last_activity > self.connection_timeout:
                            self.logger.info(
                                f"WORKER {worker_id}: Connection {connection_id} timed out, closing"
                            )
                            await self.close_connection(connection_id, "timeout")
                    except Exception as e:
                        self.logger.error(
                            "Error checking connection timeout",
                            connection_id=connection_id,
                            error=str(e),
                        )

                # Clean up old event buffers in Redis
                buffer_timeout = 3600  # 1 hour
                buffer_pattern = f"{self.redis_buffers_key}:*"

                try:
                    # This try block is for the buffer cleanup operations
                    # Use SCAN instead of KEYS (which is disabled for security)
                    cursor = "0"
                    buffer_keys: List[Any] = []
                    while True:
                        # SCAN with pattern matching
                        result = await self.redis.scan(
                            cursor=cursor, match=buffer_pattern, count=100
                        )
                        cursor, keys = result
                        buffer_keys.extend(keys)

                        # Break when cursor returns to 0 (scan complete)
                        if cursor == 0:
                            break

                    for buffer_key_bytes in buffer_keys:
                        buffer_key: str = _safe_decode(buffer_key_bytes)
                        # Extract connection ID from buffer key
                        connection_id = buffer_key.split(":")[-1]

                        # Check if connection still exists
                        if not await self._connection_exists(connection_id):
                            # Connection doesn't exist, check if buffer is old enough to delete
                            buffer_age = (
                                now  # Since we don't track buffer creation time, assume they're old
                            )
                            if buffer_age > buffer_timeout:
                                await self.redis.delete(buffer_key)
                                self.logger.info(
                                    f"WORKER {worker_id}: Cleaned up old buffer for connection {connection_id}"
                                )
                except Exception as e:
                    import os

                    worker_id = os.getpid()
                    self.logger.error(
                        f"WORKER {worker_id}: Error cleaning up Redis buffers",
                        error=str(e),
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"WORKER {worker_id}: Error in cleanup loop",
                    error=str(e),
                )
                await asyncio.sleep(5)  # Wait before retrying

    async def get_connection_status(self, connection_id: str) -> bool:
        """
        Check if a connection exists and is active.

        Args:
            connection_id: Connection ID to check

        Returns:
            True if connection exists and is active
        """
        return await self._connection_exists(connection_id)

    async def get_connection_metadata(self, connection_id: str) -> Optional[SSEConnectionMetadata]:
        """
        Get connection metadata.

        Args:
            connection_id: Connection ID

        Returns:
            Connection metadata if found, None otherwise
        """
        connection_data = await self._get_connection_data(connection_id)
        if not connection_data:
            return None

        metadata_dict = connection_data.get("metadata", {})
        if not metadata_dict:
            return None

        try:
            # Convert ISO datetime strings back to datetime objects
            if "connected_at" in metadata_dict and isinstance(metadata_dict["connected_at"], str):
                metadata_dict["connected_at"] = datetime.fromisoformat(
                    metadata_dict["connected_at"].replace("Z", "+00:00")
                )
            if "last_heartbeat" in metadata_dict and isinstance(
                metadata_dict["last_heartbeat"], str
            ):
                metadata_dict["last_heartbeat"] = datetime.fromisoformat(
                    metadata_dict["last_heartbeat"].replace("Z", "+00:00")
                )

            # Create metadata object
            return SSEConnectionMetadata(**metadata_dict)
        except Exception as e:
            self.logger.error(
                f"Failed to parse connection metadata for {connection_id}: {e}",
                metadata_dict=metadata_dict,
            )
            return None

    async def get_connection_count(self) -> int:
        """
        Get the total number of active connections.

        Returns:
            Number of active connections
        """
        return await self.redis.hlen(self.redis_connections_key)


# Singleton pattern for SSE connection manager
_connection_manager: Optional[SSEConnectionManager] = None


async def get_sse_connection_manager() -> SSEConnectionManager:
    """
    Get or create the SSE connection manager singleton.

    Returns:
        SSEConnectionManager: The shared connection manager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = SSEConnectionManager()
    return _connection_manager


async def close_sse_connection_manager() -> None:
    """
    Close the SSE connection manager singleton.
    """
    global _connection_manager
    if _connection_manager is not None:
        # Cancel background tasks
        if _connection_manager.heartbeat_task:
            _connection_manager.heartbeat_task.cancel()

        if _connection_manager.cleanup_task:
            _connection_manager.cleanup_task.cancel()

        if _connection_manager.redis_pubsub_task:
            _connection_manager.redis_pubsub_task.cancel()

        # Close Redis connection
        await _connection_manager.redis.close()

        # Clear singleton
        _connection_manager = None

        logger.info("SSE connection manager closed")
