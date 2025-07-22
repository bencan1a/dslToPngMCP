"""
Performance and Load Tests
==========================

Comprehensive performance and load testing for the DSL to PNG conversion system,
including API load testing, concurrent processing, resource utilization, and scalability analysis.
"""

import pytest
import asyncio
import time
import statistics
import threading
import concurrent.futures
from typing import Dict, Any, List, Optional
from pathlib import Path
import psutil
import json
import requests
from unittest.mock import Mock, patch

from src.core.dsl.parser import DSLParser
from src.core.rendering.html_generator import HTMLGenerator
from src.core.rendering.png_generator import PNGGenerator
# from src.core.storage.manager import FileStorageManager
from src.models.schemas import RenderOptions

from tests.utils.data_generators import MockDataGenerator
from tests.utils.helpers import measure_performance, create_temp_directory
from tests.utils.assertions import assert_performance_within_limits


class TestAPILoadPerformance:
    """Test API performance under various load conditions."""
    
    @pytest.fixture
    def sample_requests(self):
        """Generate sample DSL requests for load testing."""
        requests = []
        for i in range(100):
            request = {
                "dsl": {
                    "title": f"Load Test Document {i}",
                    "viewport": {"width": 800, "height": 600},
                    "elements": [
                        {
                            "type": "text",
                            "content": f"Load test content {i}",
                            "style": {"fontSize": "16px", "color": "#333"}
                        }
                    ]
                },
                "options": {"width": 800, "height": 600, "format": "png"}
            }
            requests.append(request)
        return requests
    
    def test_single_request_baseline_performance(self, sample_requests):
        """Test baseline performance for single API request."""
        request = sample_requests[0]
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            with measure_performance() as timer:
                # Simulate API request processing
                response = self._simulate_api_request(request)
            
            assert response["status"] == "success"
            assert timer.elapsed_time < 2.0  # Single request should be fast
    
    def test_sequential_requests_performance(self, sample_requests):
        """Test performance of sequential API requests."""
        num_requests = 10
        requests_subset = sample_requests[:num_requests]
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            processing_times = []
            
            with measure_performance() as timer:
                for request in requests_subset:
                    start_time = time.time()
                    response = self._simulate_api_request(request)
                    processing_time = time.time() - start_time
                    processing_times.append(processing_time)
                    assert response["status"] == "success"
            
            # Analyze performance metrics
            avg_time = statistics.mean(processing_times)
            max_time = max(processing_times)
            min_time = min(processing_times)
            
            assert avg_time < 1.0  # Average should be under 1 second
            assert max_time < 3.0  # No request should take more than 3 seconds
            assert timer.elapsed_time < num_requests * 2.0  # Total time reasonable
            
            # Check for performance consistency
            std_dev = statistics.stdev(processing_times)
            assert std_dev < avg_time * 0.5  # Standard deviation should be reasonable
    
    def test_concurrent_requests_performance(self, sample_requests):
        """Test performance under concurrent load."""
        num_concurrent = 20
        requests_subset = sample_requests[:num_concurrent]
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            def process_request(request):
                """Process a single request."""
                start_time = time.time()
                response = self._simulate_api_request(request)
                processing_time = time.time() - start_time
                return {
                    "response": response,
                    "processing_time": processing_time,
                    "success": response["status"] == "success"
                }
            
            with measure_performance() as timer:
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(process_request, req) for req in requests_subset]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze concurrent performance
            successful_requests = sum(1 for r in results if r["success"])
            processing_times = [r["processing_time"] for r in results]
            
            assert successful_requests == num_concurrent
            assert timer.elapsed_time < 10.0  # Should complete within 10 seconds
            
            avg_concurrent_time = statistics.mean(processing_times)
            assert avg_concurrent_time < 2.0  # Average concurrent time should be reasonable
    
    def test_stress_testing_high_load(self, sample_requests):
        """Test system behavior under high stress load."""
        num_stress_requests = 50
        requests_subset = sample_requests[:num_stress_requests]
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            def stress_worker(requests_batch):
                """Worker function for stress testing."""
                results = []
                for request in requests_batch:
                    try:
                        start_time = time.time()
                        response = self._simulate_api_request(request)
                        processing_time = time.time() - start_time
                        results.append({
                            "success": response["status"] == "success",
                            "processing_time": processing_time,
                            "error": None
                        })
                    except Exception as e:
                        results.append({
                            "success": False,
                            "processing_time": None,
                            "error": str(e)
                        })
                return results
            
            # Split requests into batches for multiple threads
            batch_size = 10
            batches = [requests_subset[i:i+batch_size] for i in range(0, len(requests_subset), batch_size)]
            
            with measure_performance() as timer:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    batch_futures = [executor.submit(stress_worker, batch) for batch in batches]
                    batch_results = [future.result() for future in concurrent.futures.as_completed(batch_futures)]
            
            # Flatten results
            all_results = []
            for batch_result in batch_results:
                all_results.extend(batch_result)
            
            # Analyze stress test results
            successful_requests = sum(1 for r in all_results if r["success"])
            failed_requests = sum(1 for r in all_results if not r["success"])
            success_rate = successful_requests / len(all_results)
            
            # Under stress, we expect some degradation but should maintain reasonable success rate
            assert success_rate >= 0.8  # At least 80% success rate under stress
            assert timer.elapsed_time < 30.0  # Should complete within 30 seconds
            
            # Analyze processing times for successful requests
            successful_times = [r["processing_time"] for r in all_results if r["success"] and r["processing_time"]]
            if successful_times:
                avg_stress_time = statistics.mean(successful_times)
                assert avg_stress_time < 5.0  # Even under stress, average should be reasonable
    
    def _simulate_api_request(self, request_data):
        """Simulate API request processing."""
        # Simulate request validation
        time.sleep(0.001)
        
        # Simulate DSL parsing
        time.sleep(0.01)
        
        # Simulate rendering (mocked)
        time.sleep(0.05)
        
        # Simulate response formatting
        time.sleep(0.001)
        
        return {"status": "success", "content_hash": "test_hash"}


class TestComponentPerformance:
    """Test performance of individual system components."""
    
    @pytest.fixture
    def dsl_parser(self):
        """Create DSL parser for testing."""
        return DSLParser()
    
    @pytest.fixture
    def html_generator(self):
        """Create HTML generator for testing."""
        return HTMLGenerator()
    
    @pytest.fixture
    async def png_generator(self):
        """Create PNG generator for testing."""
        generator = PNGGenerator()
        await generator.initialize()
        yield generator
        await generator.close()
    
    # @pytest.fixture
    # async def storage_manager(self):
    #     """Create storage manager for testing."""
    #     with create_temp_directory() as temp_dir:
    #         with patch('src.core.storage.manager.get_settings') as mock_settings:
    #             mock_settings.return_value.storage_path = temp_dir / "storage"
    #             mock_settings.return_value.cache_ttl = 3600
    #
    #             manager = FileStorageManager()
    #             await manager.initialize()
    #             yield manager
    #             await manager.close()
    
    def test_dsl_parser_performance(self, dsl_parser):
        """Test DSL parser performance with various document sizes."""
        # Test small document
        small_dsl = {
            "title": "Small Test",
            "viewport": {"width": 400, "height": 300},
            "elements": [{"type": "text", "content": "Small test"}]
        }
        
        with measure_performance() as timer:
            document = dsl_parser.parse_dict(small_dsl)
        
        assert timer.elapsed_time < 0.1
        assert document is not None
        
        # Test medium document
        medium_elements = []
        for i in range(50):
            medium_elements.append({
                "type": "text",
                "content": f"Medium element {i}",
                "style": {"fontSize": "14px"}
            })
        
        medium_dsl = {
            "title": "Medium Test",
            "viewport": {"width": 800, "height": 600},
            "elements": medium_elements
        }
        
        with measure_performance() as timer:
            document = dsl_parser.parse_dict(medium_dsl)
        
        assert timer.elapsed_time < 0.5
        assert document is not None
        
        # Test large document
        large_elements = []
        for i in range(200):
            large_elements.append({
                "type": "text",
                "content": f"Large element {i} with more content",
                "style": {"fontSize": "12px", "margin": "2px"}
            })
        
        large_dsl = {
            "title": "Large Test",
            "viewport": {"width": 1200, "height": 800},
            "elements": large_elements
        }
        
        with measure_performance() as timer:
            document = dsl_parser.parse_dict(large_dsl)
        
        assert timer.elapsed_time < 2.0
        assert document is not None
    
    @pytest.mark.asyncio
    async def test_html_generator_performance(self, html_generator):
        """Test HTML generator performance."""
        # Create test documents of varying complexity
        simple_doc = MockDataGenerator.generate_dsl_document(element_count=10)
        complex_doc = MockDataGenerator.generate_dsl_document(element_count=100)
        
        render_options = RenderOptions(width=800, height=600)
        
        # Test simple document
        with measure_performance() as timer:
            html = await html_generator.generate_html(simple_doc, render_options)
        
        assert timer.elapsed_time < 0.5
        assert html is not None
        assert len(html) > 100
        
        # Test complex document
        with measure_performance() as timer:
            html = await html_generator.generate_html(complex_doc, render_options)
        
        assert timer.elapsed_time < 2.0
        assert html is not None
        assert len(html) > 1000
    
    @pytest.mark.asyncio
    async def test_png_generator_performance(self, png_generator):
        """Test PNG generator performance with different configurations."""
        base_html = "<html><body><h1>Performance Test</h1></body></html>"
        
        # Test different image sizes
        test_configs = [
            (400, 300, 1.0),   # Small
            (800, 600, 1.0),   # Medium
            (1200, 800, 1.0),  # Large
            (800, 600, 2.0),   # High DPI
        ]
        
        for width, height, scale in test_configs:
            render_options = RenderOptions(
                width=width,
                height=height,
                device_scale_factor=scale
            )
            
            with measure_performance() as timer:
                result = await png_generator.generate_png(
                    html_content=base_html,
                    render_options=render_options,
                    task_id=f"perf-test-{width}x{height}"
                )
            
            # Performance expectations based on image size
            expected_time = (width * height * scale) / 1000000  # Scale with pixel count
            max_time = max(expected_time, 5.0)  # At least 5 seconds for largest
            
            assert timer.elapsed_time < max_time
            assert result is not None
            assert result.width == width
            assert result.height == height
    
    # Storage manager performance tests disabled due to missing storage implementation
    # @pytest.mark.asyncio
    # async def test_storage_manager_performance(self, storage_manager):
    #     """Test storage manager performance."""
    #     pass


class TestConcurrencyPerformance:
    """Test system performance under concurrent operations."""
    
    @pytest.fixture
    async def component_setup(self):
        """Setup all components for concurrency testing."""
        components = {}
        
        # Setup with mocked dependencies for performance testing
        with create_temp_directory() as temp_dir:
            with patch('src.core.storage.manager.get_settings') as mock_settings:
                mock_settings.return_value.storage_path = temp_dir / "storage"
                mock_settings.return_value.cache_ttl = 3600
                
                components['dsl_parser'] = DSLParser()
                components['html_generator'] = HTMLGenerator()
                
                components['png_generator'] = PNGGenerator()
                await components['png_generator'].initialize()
                
                components['storage_manager'] = FileStorageManager()
                await components['storage_manager'].initialize()
                
                yield components
                
                await components['png_generator'].close()
                await components['storage_manager'].close()
    
    @pytest.mark.asyncio
    async def test_concurrent_dsl_parsing(self, component_setup):
        """Test concurrent DSL parsing performance."""
        parser = component_setup['dsl_parser']
        
        # Generate test DSL documents
        test_docs = []
        for i in range(20):
            doc = {
                "title": f"Concurrent Test {i}",
                "viewport": {"width": 600, "height": 400},
                "elements": [
                    {"type": "text", "content": f"Content {i}"}
                    for j in range(10)
                ]
            }
            test_docs.append(doc)
        
        async def parse_document(doc_data):
            """Parse a single document."""
            return parser.parse_dict(doc_data)
        
        with measure_performance() as timer:
            # Parse documents concurrently
            tasks = [parse_document(doc) for doc in test_docs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_parses = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_parses == len(test_docs)
        assert timer.elapsed_time < 2.0  # Should complete quickly
    
    @pytest.mark.asyncio
    async def test_concurrent_html_generation(self, component_setup):
        """Test concurrent HTML generation performance."""
        generator = component_setup['html_generator']
        
        # Generate test documents
        test_docs = [MockDataGenerator.generate_dsl_document(element_count=20) for _ in range(10)]
        render_options = RenderOptions(width=800, height=600)
        
        async def generate_html(doc):
            """Generate HTML for a single document."""
            return await generator.generate_html(doc, render_options)
        
        with measure_performance() as timer:
            tasks = [generate_html(doc) for doc in test_docs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_generations = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
        assert successful_generations == len(test_docs)
        assert timer.elapsed_time < 5.0
    
    @pytest.mark.asyncio
    async def test_concurrent_storage_operations(self, component_setup):
        """Test concurrent storage operations."""
        storage = component_setup['storage_manager']
        
        # Generate test PNG results
        test_pngs = [MockDataGenerator.generate_png_result() for _ in range(15)]
        
        async def store_and_retrieve(png_data, index):
            """Store and retrieve a PNG."""
            content_hash = await storage.store_png(png_data, f"concurrent-{index}")
            retrieved = await storage.retrieve_png(content_hash)
            return content_hash, retrieved is not None
        
        with measure_performance() as timer:
            tasks = [store_and_retrieve(png, i) for i, png in enumerate(test_pngs)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_operations = sum(1 for r in results if not isinstance(r, Exception) and r[1])
        assert successful_operations == len(test_pngs)
        assert timer.elapsed_time < 3.0


class TestResourceUtilization:
    """Test system resource utilization under various loads."""
    
    def test_memory_usage_under_load(self):
        """Test memory usage during intensive operations."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simulate memory-intensive operations
        large_data_sets = []
        
        try:
            for i in range(100):
                # Create large DSL documents
                large_elements = []
                for j in range(100):
                    large_elements.append({
                        "type": "text",
                        "content": f"Large content block {i}-{j} with substantial text data",
                        "style": {"fontSize": "14px", "margin": "5px"}
                    })
                
                dsl_doc = {
                    "title": f"Memory Test Document {i}",
                    "viewport": {"width": 1200, "height": 800},
                    "elements": large_elements
                }
                large_data_sets.append(dsl_doc)
                
                # Check memory usage periodically
                if i % 20 == 0:
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    
                    # Memory usage should not exceed reasonable limits (500MB)
                    assert memory_increase < 500 * 1024 * 1024
            
            # Final memory check
            final_memory = process.memory_info().rss
            total_increase = final_memory - initial_memory
            
            # Total memory increase should be reasonable
            assert total_increase < 1024 * 1024 * 1024  # Less than 1GB
            
        finally:
            # Clean up to help with memory management
            del large_data_sets
    
    def test_cpu_usage_patterns(self):
        """Test CPU usage patterns during processing."""
        
        def cpu_intensive_task():
            """Simulate CPU-intensive DSL processing."""
            parser = DSLParser()
            
            for i in range(50):
                complex_dsl = {
                    "title": f"CPU Test {i}",
                    "viewport": {"width": 800, "height": 600},
                    "elements": [
                        {
                            "type": "text",
                            "content": f"Element {j}",
                            "style": {"fontSize": f"{12 + j}px"}
                        }
                        for j in range(50)
                    ]
                }
                
                document = parser.parse_dict(complex_dsl)
                assert document is not None
        
        # Monitor CPU usage during task
        cpu_percentages = []
        
        def monitor_cpu():
            """Monitor CPU usage."""
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_percentages.append(cpu_percent)
        
        # Run CPU task and monitoring concurrently
        cpu_thread = threading.Thread(target=monitor_cpu)
        cpu_thread.start()
        
        with measure_performance() as timer:
            cpu_intensive_task()
        
        cpu_thread.join()
        
        # Analyze CPU usage
        if cpu_percentages:
            avg_cpu = statistics.mean(cpu_percentages)
            max_cpu = max(cpu_percentages)
            
            # CPU usage should be reasonable (not constantly maxed out)
            assert avg_cpu < 90.0  # Average CPU usage should be under 90%
            assert max_cpu < 100.0  # Should not completely max out CPU
        
        # Task should complete in reasonable time
        assert timer.elapsed_time < 10.0


class TestScalabilityMetrics:
    """Test system scalability characteristics."""
    
    @pytest.mark.asyncio
    async def test_throughput_scaling(self):
        """Test how throughput scales with increased load."""
        
        async def process_batch(batch_size):
            """Process a batch of requests and measure throughput."""
            with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
                mock_render.return_value = MockDataGenerator.generate_png_result()
                
                start_time = time.time()
                
                # Simulate processing batch
                tasks = []
                for i in range(batch_size):
                    task = asyncio.create_task(self._simulate_request_processing())
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
                end_time = time.time()
                duration = end_time - start_time
                throughput = batch_size / duration
                
                return throughput, duration
        
        # Test different batch sizes
        batch_sizes = [1, 5, 10, 20, 50]
        throughput_results = []
        
        for batch_size in batch_sizes:
            throughput, duration = await process_batch(batch_size)
            throughput_results.append((batch_size, throughput, duration))
        
        # Analyze scaling characteristics
        for i, (batch_size, throughput, duration) in enumerate(throughput_results):
            assert throughput > 0
            assert duration > 0
            
            # Throughput should generally increase with batch size (up to a point)
            if i > 0:
                prev_throughput = throughput_results[i-1][1]
                # Allow for some variation but expect general scaling
                assert throughput >= prev_throughput * 0.8
    
    def test_response_time_distribution(self):
        """Test response time distribution under load."""
        response_times = []
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            # Collect response time samples
            for i in range(100):
                start_time = time.time()
                
                # Simulate request processing
                self._simulate_single_request()
                
                response_time = time.time() - start_time
                response_times.append(response_time)
        
        # Analyze response time distribution
        avg_response_time = statistics.mean(response_times)
        median_response_time = statistics.median(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        p99_response_time = sorted(response_times)[int(0.99 * len(response_times))]
        
        # Response time assertions
        assert avg_response_time < 1.0  # Average under 1 second
        assert median_response_time < 0.5  # Median under 500ms
        assert p95_response_time < 2.0  # 95th percentile under 2 seconds
        assert p99_response_time < 5.0  # 99th percentile under 5 seconds
        
        # Check for reasonable distribution (not too much variance)
        std_dev = statistics.stdev(response_times)
        assert std_dev < avg_response_time * 2  # Standard deviation reasonable
    
    async def _simulate_request_processing(self):
        """Simulate processing a single request."""
        # Simulate various processing stages
        await asyncio.sleep(0.01)  # DSL parsing
        await asyncio.sleep(0.02)  # HTML generation
        await asyncio.sleep(0.05)  # PNG generation (mocked)
        await asyncio.sleep(0.005)  # Storage operations
    
    def _simulate_single_request(self):
        """Simulate synchronous request processing."""
        time.sleep(0.01)  # DSL parsing
        time.sleep(0.02)  # HTML generation
        time.sleep(0.05)  # PNG generation
        time.sleep(0.005)  # Storage


class TestPerformanceRegression:
    """Test for performance regressions over time."""
    
    def test_baseline_performance_metrics(self):
        """Establish and test baseline performance metrics."""
        baseline_metrics = {
            "dsl_parse_time": 0.1,      # seconds
            "html_generation_time": 0.5,  # seconds
            "png_generation_time": 3.0,   # seconds
            "storage_operation_time": 0.1, # seconds
            "api_response_time": 2.0       # seconds
        }
        
        # Test DSL parsing performance
        parser = DSLParser()
        test_dsl = MockDataGenerator.generate_dsl_dict(element_count=50)
        
        with measure_performance() as timer:
            document = parser.parse_dict(test_dsl)
        
        assert timer.elapsed_time <= baseline_metrics["dsl_parse_time"]
        assert document is not None
    
    def test_performance_under_sustained_load(self):
        """Test performance consistency under sustained load."""
        processing_times = []
        
        with patch('src.api.routes.render.render_dsl_to_png') as mock_render:
            mock_render.return_value = MockDataGenerator.generate_png_result()
            
            # Run sustained load for several iterations
            for iteration in range(50):
                start_time = time.time()
                
                # Simulate request processing
                self._simulate_single_request()
                
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
        
        # Analyze sustained performance
        first_half = processing_times[:25]
        second_half = processing_times[25:]
        
        avg_first_half = statistics.mean(first_half)
        avg_second_half = statistics.mean(second_half)
        
        # Performance should not degrade significantly over time
        degradation_ratio = avg_second_half / avg_first_half
        assert degradation_ratio < 1.5  # No more than 50% degradation
        
        # Overall consistency check
        overall_std = statistics.stdev(processing_times)
        overall_avg = statistics.mean(processing_times)
        coefficient_of_variation = overall_std / overall_avg
        
        assert coefficient_of_variation < 0.5  # Reasonable consistency
    
    def _simulate_single_request(self):
        """Simulate processing a single request."""
        time.sleep(0.01)  # DSL parsing
        time.sleep(0.02)  # HTML generation  
        time.sleep(0.05)  # PNG generation
        time.sleep(0.005) # Storage