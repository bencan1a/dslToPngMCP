"""
SSE Performance Tests
====================

Performance and scalability testing for Server-Sent Events including:
- Concurrent connections (10, 25, 50 simultaneous SSE connections)
- Event throughput measurement and latency under load
- Memory usage monitoring and connection overhead
- Long-running connection tests (5+ minutes) with periodic activity
- Browser pool impact verification
"""

import pytest
import pytest_asyncio
import asyncio
import time
import uuid
import psutil
import gc
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from unittest.mock import patch

from src.api.sse.events import (
    SSEEventType, create_progress_event, create_heartbeat_event,
    create_tool_call_event, create_tool_response_event
)

from tests.fixtures.sse_fixtures import (
    sse_test_environment, performance_config, mock_sse_client,
    MockSSEConnectionManager
)
from tests.utils.helpers import (
    measure_async_performance, get_memory_usage, get_system_info,
    ConcurrentExecutor
)
from tests.utils.assertions import (
    assert_performance_within_threshold, assert_memory_usage_reasonable
)


@pytest.mark.performance
@pytest.mark.sse
class TestSSEConnectionPerformance:
    """Test SSE connection performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_establishment(self, sse_test_environment, performance_config):
        """Test establishing multiple concurrent SSE connections."""
        connection_counts = performance_config['concurrent_connections']
        
        for target_connections in connection_counts:
            print(f"\n--- Testing {target_connections} concurrent connections ---")
            
            start_memory = get_memory_usage()
            connection_ids = []
            
            async def create_single_connection(index: int) -> str:
                """Create a single SSE connection."""
                connection_id = await sse_test_environment.create_connection(f"perf-conn-{index}")
                
                # Send initial heartbeat to establish connection
                heartbeat_event = create_heartbeat_event(connection_id, 0.0)
                await sse_test_environment.connection_manager.send_to_connection(connection_id, heartbeat_event)
                
                return connection_id
            
            # Measure connection establishment time
            with measure_async_performance() as timer:
                tasks = [create_single_connection(i) for i in range(target_connections)]
                connection_ids = await asyncio.gather(*tasks)
            
            # Verify all connections established
            assert len(connection_ids) == target_connections
            active_connections = await sse_test_environment.connection_manager.get_connection_count()
            assert active_connections == target_connections
            
            # Measure memory usage
            end_memory = get_memory_usage()
            memory_per_connection = (end_memory - start_memory) / target_connections if target_connections > 0 else 0
            
            print(f"Connection establishment time: {timer.elapsed_time:.3f}s")
            print(f"Memory per connection: {memory_per_connection:.2f}MB")
            print(f"Connections per second: {target_connections / timer.elapsed_time:.1f}")
            
            # Performance assertions
            max_time_per_connection = 0.1  # 100ms per connection should be sufficient
            assert_performance_within_threshold(timer.elapsed_time, target_connections * max_time_per_connection)
            
            # Memory usage should be reasonable (< 5MB per connection)
            if target_connections > 10:  # Only check for larger connection counts
                assert memory_per_connection < 5.0, f"Memory usage {memory_per_connection:.2f}MB per connection is too high"
            
            # Cleanup for next iteration
            await sse_test_environment.cleanup_connections()
            gc.collect()  # Force garbage collection
    
    @pytest.mark.asyncio
    async def test_connection_throughput_under_load(self, sse_test_environment):
        """Test connection throughput under sustained load."""
        connection_count = 25
        events_per_connection = 100
        total_events = connection_count * events_per_connection
        
        # Create connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"throughput-{i}")
            connection_ids.append(connection_id)
        
        # Function to send events to a connection
        async def send_events_to_connection(connection_id: str, start_index: int):
            """Send multiple events to a single connection."""
            for i in range(events_per_connection):
                event_index = start_index + i
                progress_event = create_progress_event(
                    connection_id, "throughput_test", event_index % 100, 
                    f"Event {event_index}", "performance_test"
                )
                await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
                
                # Small delay to prevent overwhelming
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
        
        # Send events concurrently to all connections
        with measure_async_performance() as timer:
            tasks = []
            for i, connection_id in enumerate(connection_ids):
                start_index = i * events_per_connection
                task = send_events_to_connection(connection_id, start_index)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        # Calculate throughput metrics
        events_per_second = total_events / timer.elapsed_time
        latency_per_event = timer.elapsed_time / total_events
        
        print(f"\n--- Throughput Test Results ---")
        print(f"Total events: {total_events}")
        print(f"Total time: {timer.elapsed_time:.3f}s")
        print(f"Events per second: {events_per_second:.1f}")
        print(f"Average latency per event: {latency_per_event * 1000:.2f}ms")
        
        # Verify all events were delivered
        total_received = 0
        for connection_id in connection_ids:
            client_events = await sse_test_environment.get_connection_events(connection_id)
            total_received += len(client_events)
        
        assert total_received == total_events, f"Expected {total_events} events, received {total_received}"
        
        # Performance assertions
        assert events_per_second > 1000, f"Throughput {events_per_second:.1f} events/sec is too low"
        assert latency_per_event < 0.01, f"Average latency {latency_per_event * 1000:.2f}ms is too high"
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, sse_test_environment):
        """Test memory usage stability over extended operation."""
        connection_count = 20
        test_duration = 60  # 1 minute test
        memory_samples = []
        
        # Create connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"memory-test-{i}")
            connection_ids.append(connection_id)
        
        initial_memory = get_memory_usage()
        start_time = time.time()
        
        # Run sustained activity for test duration
        while time.time() - start_time < test_duration:
            cycle_start = time.time()
            
            # Send events to all connections
            for connection_id in connection_ids:
                progress_event = create_progress_event(
                    connection_id, "memory_test", 
                    int((time.time() - start_time) / test_duration * 100),
                    "Memory stability test", "testing"
                )
                await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
            
            # Sample memory usage
            current_memory = get_memory_usage()
            memory_samples.append(current_memory)
            
            # Wait for next cycle (target: 10 cycles per second)
            cycle_time = time.time() - cycle_start
            if cycle_time < 0.1:
                await asyncio.sleep(0.1 - cycle_time)
        
        final_memory = get_memory_usage()
        
        # Analyze memory usage
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        memory_growth = final_memory - initial_memory
        memory_variance = max_memory - min_memory
        
        print(f"\n--- Memory Stability Test Results ---")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Memory growth: {memory_growth:.2f}MB")
        print(f"Average memory: {avg_memory:.2f}MB")
        print(f"Memory variance: {memory_variance:.2f}MB")
        print(f"Test duration: {test_duration}s")
        print(f"Memory samples: {len(memory_samples)}")
        
        # Memory stability assertions
        assert memory_growth < 50.0, f"Memory growth {memory_growth:.2f}MB indicates memory leak"
        assert memory_variance < 100.0, f"Memory variance {memory_variance:.2f}MB indicates instability"
        assert_memory_usage_reasonable(final_memory, 1000.0)  # Max 1GB total
    
    @pytest.mark.asyncio
    async def test_long_running_connections(self, sse_test_environment):
        """Test long-running SSE connections with periodic activity."""
        connection_count = 10
        test_duration = 300  # 5 minutes
        heartbeat_interval = 30  # 30 seconds
        
        print(f"\n--- Starting {test_duration}s long-running connection test ---")
        
        # Create long-running connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"long-running-{i}")
            connection_ids.append(connection_id)
        
        start_time = time.time()
        heartbeat_count = 0
        connection_drops = 0
        
        # Maintain connections with periodic activity
        while time.time() - start_time < test_duration:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Send heartbeat to all connections
            active_connections = []
            for connection_id in connection_ids:
                try:
                    heartbeat_event = create_heartbeat_event(connection_id, elapsed)
                    await sse_test_environment.connection_manager.send_to_connection(connection_id, heartbeat_event)
                    active_connections.append(connection_id)
                except Exception:
                    connection_drops += 1
            
            heartbeat_count += 1
            
            # Send periodic progress updates
            for i, connection_id in enumerate(active_connections):
                if i % 3 == heartbeat_count % 3:  # Rotate which connections get updates
                    progress = int(elapsed / test_duration * 100)
                    progress_event = create_progress_event(
                        connection_id, "long_running_test", progress,
                        f"Long running test {elapsed:.0f}s", "sustained_operation"
                    )
                    await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
            
            # Progress reporting
            if heartbeat_count % 10 == 0:  # Every 10 heartbeats
                progress_pct = (elapsed / test_duration) * 100
                print(f"Progress: {progress_pct:.1f}% ({elapsed:.0f}s/{test_duration}s), Active: {len(active_connections)}")
            
            # Wait for next heartbeat interval
            await asyncio.sleep(heartbeat_interval)
        
        final_connections = await sse_test_environment.connection_manager.get_connection_count()
        
        print(f"\n--- Long-running Test Results ---")
        print(f"Test duration: {test_duration}s")
        print(f"Heartbeats sent: {heartbeat_count}")
        print(f"Connection drops: {connection_drops}")
        print(f"Final active connections: {final_connections}")
        print(f"Connection survival rate: {(final_connections / connection_count) * 100:.1f}%")
        
        # Verify connection stability
        assert final_connections >= connection_count * 0.9, "Too many connections dropped during long-running test"
        assert connection_drops < connection_count * 0.2, "Connection drop rate too high"
        
        # Verify events were delivered consistently
        for connection_id in connection_ids[:min(3, len(connection_ids))]:  # Check first 3 connections
            try:
                client_events = await sse_test_environment.get_connection_events(connection_id)
                heartbeat_events = [e for e in client_events if e['type'] == SSEEventType.CONNECTION_HEARTBEAT]
                progress_events = [e for e in client_events if e['type'] == SSEEventType.RENDER_PROGRESS]
                
                # Should have received most heartbeats
                assert len(heartbeat_events) >= heartbeat_count * 0.8, "Missing too many heartbeat events"
                
                print(f"Connection {connection_id[:8]}: {len(heartbeat_events)} heartbeats, {len(progress_events)} progress")
            except Exception as e:
                print(f"Failed to verify events for {connection_id}: {e}")


@pytest.mark.performance
@pytest.mark.sse
class TestSSEEventThroughput:
    """Test SSE event throughput and latency."""
    
    @pytest.mark.asyncio
    async def test_high_frequency_event_streams(self, sse_test_environment):
        """Test high-frequency event streaming performance."""
        connection_id = await sse_test_environment.create_connection()
        
        # Test different event frequencies
        test_scenarios = [
            (1000, "1K events"),
            (5000, "5K events"),
            (10000, "10K events")
        ]
        
        for event_count, description in test_scenarios:
            print(f"\n--- Testing {description} ---")
            
            # Clear previous events
            await sse_test_environment.connection_manager.connections[connection_id].clear_events()
            
            # Send high-frequency events
            with measure_async_performance() as timer:
                for i in range(event_count):
                    progress_event = create_progress_event(
                        connection_id, "high_freq_test", i % 100, 
                        f"High frequency event {i}", "performance"
                    )
                    await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
                    
                    # Micro-delay every 100 events to prevent overwhelming
                    if i % 100 == 0 and i > 0:
                        await asyncio.sleep(0.001)
            
            # Verify all events delivered
            client_events = await sse_test_environment.get_connection_events(connection_id)
            assert len(client_events) == event_count, f"Expected {event_count}, got {len(client_events)}"
            
            # Calculate performance metrics
            events_per_second = event_count / timer.elapsed_time
            avg_latency_ms = (timer.elapsed_time / event_count) * 1000
            
            print(f"Events per second: {events_per_second:.1f}")
            print(f"Average latency: {avg_latency_ms:.3f}ms")
            print(f"Total time: {timer.elapsed_time:.3f}s")
            
            # Performance assertions based on event count
            if event_count <= 1000:
                assert events_per_second > 5000, f"Low throughput for {description}: {events_per_second:.1f} eps"
            elif event_count <= 5000:
                assert events_per_second > 3000, f"Low throughput for {description}: {events_per_second:.1f} eps"
            else:
                assert events_per_second > 2000, f"Low throughput for {description}: {events_per_second:.1f} eps"
            
            assert avg_latency_ms < 1.0, f"High latency for {description}: {avg_latency_ms:.3f}ms"
    
    @pytest.mark.asyncio
    async def test_event_latency_under_concurrent_load(self, sse_test_environment):
        """Test event latency under concurrent connection load."""
        connection_count = 20
        events_per_connection = 50
        
        # Create multiple connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"latency-test-{i}")
            connection_ids.append(connection_id)
        
        # Measure latency for each connection
        latency_measurements = []
        
        async def measure_connection_latency(connection_id: str, index: int):
            """Measure event latency for a single connection."""
            connection_latencies = []
            
            for i in range(events_per_connection):
                send_time = time.perf_counter()
                
                progress_event = create_progress_event(
                    connection_id, "latency_test", i * 2, 
                    f"Latency test {index}-{i}", "latency_measurement"
                )
                await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
                
                # Simulate processing time
                receive_time = time.perf_counter()
                latency = (receive_time - send_time) * 1000  # Convert to milliseconds
                connection_latencies.append(latency)
                
                # Small delay between events
                await asyncio.sleep(0.02)
            
            return connection_latencies
        
        # Execute latency measurements concurrently
        with measure_async_performance() as timer:
            tasks = [measure_connection_latency(conn_id, i) for i, conn_id in enumerate(connection_ids)]
            all_latencies = await asyncio.gather(*tasks)
        
        # Flatten latency measurements
        for connection_latencies in all_latencies:
            latency_measurements.extend(connection_latencies)
        
        # Calculate latency statistics
        avg_latency = sum(latency_measurements) / len(latency_measurements)
        max_latency = max(latency_measurements)
        min_latency = min(latency_measurements)
        p95_latency = sorted(latency_measurements)[int(len(latency_measurements) * 0.95)]
        
        print(f"\n--- Latency Under Load Test Results ---")
        print(f"Total events: {connection_count * events_per_connection}")
        print(f"Average latency: {avg_latency:.3f}ms")
        print(f"95th percentile latency: {p95_latency:.3f}ms")
        print(f"Min latency: {min_latency:.3f}ms")
        print(f"Max latency: {max_latency:.3f}ms")
        print(f"Total test time: {timer.elapsed_time:.3f}s")
        
        # Latency assertions
        assert avg_latency < 5.0, f"Average latency {avg_latency:.3f}ms exceeds 5ms threshold"
        assert p95_latency < 10.0, f"95th percentile latency {p95_latency:.3f}ms exceeds 10ms threshold"


@pytest.mark.performance
@pytest.mark.sse
class TestSSEBrowserPoolImpact:
    """Test impact of SSE on browser pool performance."""
    
    @pytest.mark.asyncio
    async def test_browser_pool_with_active_sse(self, sse_test_environment):
        """Test browser pool performance with active SSE connections."""
        # This test simulates browser pool operations while SSE connections are active
        connection_count = 10
        browser_operations = 20
        
        # Create SSE connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"browser-impact-{i}")
            connection_ids.append(connection_id)
        
        # Simulate browser pool operations
        async def simulate_browser_operation(index: int):
            """Simulate a browser pool operation."""
            # Simulate browser acquisition time
            await asyncio.sleep(0.1)
            
            # Simulate page load and rendering
            await asyncio.sleep(0.2)
            
            # Simulate screenshot capture
            await asyncio.sleep(0.1)
            
            # Simulate browser release
            await asyncio.sleep(0.05)
            
            return {"operation": index, "success": True}
        
        # Measure browser pool performance with active SSE
        with measure_async_performance() as timer:
            # Start sending SSE events in background
            async def send_sse_events():
                for _ in range(5):  # Send 5 rounds of events
                    for connection_id in connection_ids:
                        progress_event = create_progress_event(
                            connection_id, "browser_impact", 50, 
                            "Browser pool impact test", "testing"
                        )
                        await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
                    await asyncio.sleep(0.2)  # Wait between rounds
            
            # Run SSE events and browser operations concurrently
            sse_task = asyncio.create_task(send_sse_events())
            browser_tasks = [simulate_browser_operation(i) for i in range(browser_operations)]
            browser_results = await asyncio.gather(*browser_tasks)
            await sse_task
        
        # Calculate browser pool metrics
        operations_per_second = browser_operations / timer.elapsed_time
        avg_operation_time = timer.elapsed_time / browser_operations
        
        print(f"\n--- Browser Pool Impact Test Results ---")
        print(f"Active SSE connections: {connection_count}")
        print(f"Browser operations: {browser_operations}")
        print(f"Operations per second: {operations_per_second:.1f}")
        print(f"Average operation time: {avg_operation_time * 1000:.1f}ms")
        print(f"Total test time: {timer.elapsed_time:.3f}s")
        
        # Verify all browser operations succeeded
        assert all(result["success"] for result in browser_results)
        
        # Performance assertions
        assert operations_per_second > 2.0, f"Browser pool throughput {operations_per_second:.1f} ops/sec is too low"
        assert avg_operation_time < 1.0, f"Average operation time {avg_operation_time * 1000:.1f}ms is too high"
    
    @pytest.mark.asyncio
    async def test_sse_performance_during_rendering(self, sse_test_environment):
        """Test SSE performance during active rendering operations."""
        connection_count = 5
        render_operations = 10
        events_per_connection = 50
        
        # Create SSE connections
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"render-impact-{i}")
            connection_ids.append(connection_id)
        
        # Simulate rendering operations
        async def simulate_rendering_operation(index: int):
            """Simulate a complete rendering operation."""
            # Simulate DSL parsing
            await asyncio.sleep(0.1)
            
            # Simulate HTML generation
            await asyncio.sleep(0.2)
            
            # Simulate browser rendering (heaviest part)
            await asyncio.sleep(0.5)
            
            # Simulate PNG optimization
            await asyncio.sleep(0.1)
            
            return {"operation": index, "success": True}
        
        # Measure SSE performance during rendering
        with measure_async_performance() as timer:
            # Start rendering operations in background
            render_task = asyncio.create_task(
                asyncio.gather(*[simulate_rendering_operation(i) for i in range(render_operations)])
            )
            
            # Send SSE events while rendering is happening
            sse_latencies = []
            for i in range(events_per_connection):
                start_time = time.perf_counter()
                
                # Send events to all connections
                for connection_id in connection_ids:
                    progress_event = create_progress_event(
                        connection_id, "render_impact", i * 2, 
                        f"Event during rendering {i}", "performance_test"
                    )
                    await sse_test_environment.connection_manager.send_to_connection(connection_id, progress_event)
                
                end_time = time.perf_counter()
                sse_latencies.append((end_time - start_time) * 1000)  # ms
                
                # Small delay between event batches
                await asyncio.sleep(0.05)
            
            # Wait for rendering to complete
            await render_task
        
        # Calculate SSE performance metrics during rendering
        avg_sse_latency = sum(sse_latencies) / len(sse_latencies)
        max_sse_latency = max(sse_latencies)
        events_per_second = (events_per_connection * connection_count) / timer.elapsed_time
        
        print(f"\n--- SSE Performance During Rendering Test Results ---")
        print(f"SSE connections: {connection_count}")
        print(f"Total SSE events: {events_per_connection * connection_count}")
        print(f"Render operations: {render_operations}")
        print(f"Average SSE batch latency: {avg_sse_latency:.3f}ms")
        print(f"Maximum SSE batch latency: {max_sse_latency:.3f}ms")
        print(f"Events per second: {events_per_second:.1f}")
        print(f"Total test time: {timer.elapsed_time:.3f}s")
        
        # Performance assertions
        assert avg_sse_latency < 50.0, f"Average SSE latency {avg_sse_latency:.3f}ms is too high during rendering"
        assert events_per_second > 100.0, f"SSE throughput {events_per_second:.1f} events/sec is too low during rendering"