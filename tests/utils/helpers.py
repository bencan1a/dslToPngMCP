"""
Test Helpers
============

Helper functions for common testing operations.
"""

import asyncio
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from unittest.mock import patch, AsyncMock
import time
import psutil
import os

from src.models.schemas import DSLDocument, RenderOptions, PNGResult


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 10.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout"
) -> None:
    """Wait for a condition to become true."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return
        await asyncio.sleep(interval)
    
    raise TimeoutError(error_message)


async def wait_for_async_condition(
    condition: Callable[[], Any],
    timeout: float = 10.0,
    interval: float = 0.1,
    error_message: str = "Async condition not met within timeout"
) -> None:
    """Wait for an async condition to become true."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await condition():
            return
        await asyncio.sleep(interval)
    
    raise TimeoutError(error_message)


def create_temp_file(content: str, suffix: str = ".tmp") -> Path:
    """Create a temporary file with content."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
    temp_file.write(content)
    temp_file.flush()
    temp_file.close()
    return Path(temp_file.name)


def create_temp_directory() -> Path:
    """Create a temporary directory."""
    return Path(tempfile.mkdtemp())


def cleanup_temp_path(path: Union[str, Path]) -> None:
    """Clean up temporary file or directory."""
    path = Path(path)
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except (FileNotFoundError, PermissionError):
        pass


class TemporaryFile:
    """Context manager for temporary files."""
    
    def __init__(self, content: str, suffix: str = ".tmp"):
        self.content = content
        self.suffix = suffix
        self.path: Optional[Path] = None
    
    def __enter__(self) -> Path:
        self.path = create_temp_file(self.content, self.suffix)
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path:
            cleanup_temp_path(self.path)


class TemporaryDirectory:
    """Context manager for temporary directories."""
    
    def __init__(self):
        self.path: Optional[Path] = None
    
    def __enter__(self) -> Path:
        self.path = create_temp_directory()
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path:
            cleanup_temp_path(self.path)


def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON from file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load YAML from file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Save data as JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def save_yaml_file(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Save data as YAML file."""
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def compare_json_structures(actual: Dict[str, Any], expected: Dict[str, Any], path: str = "") -> List[str]:
    """Compare JSON structures and return list of differences."""
    differences = []
    
    # Check for missing keys in actual
    for key in expected:
        current_path = f"{path}.{key}" if path else key
        if key not in actual:
            differences.append(f"Missing key: {current_path}")
        elif isinstance(expected[key], dict) and isinstance(actual[key], dict):
            differences.extend(compare_json_structures(actual[key], expected[key], current_path))
        elif type(expected[key]) != type(actual[key]):
            differences.append(f"Type mismatch at {current_path}: expected {type(expected[key])}, got {type(actual[key])}")
    
    # Check for extra keys in actual
    for key in actual:
        current_path = f"{path}.{key}" if path else key
        if key not in expected:
            differences.append(f"Extra key: {current_path}")
    
    return differences


def normalize_dsl_content(content: str) -> str:
    """Normalize DSL content for comparison."""
    # Parse and re-serialize to normalize formatting
    try:
        data = json.loads(content)
        return json.dumps(data, sort_keys=True, separators=(',', ':'))
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(content)
            return json.dumps(data, sort_keys=True, separators=(',', ':'))
        except yaml.YAMLError:
            return content.strip()


def extract_png_metadata(png_data: bytes) -> Dict[str, Any]:
    """Extract basic metadata from PNG data."""
    if len(png_data) < 24:
        return {"error": "Invalid PNG data"}
    
    # Check PNG signature
    if png_data[:8] != b'\x89PNG\r\n\x1a\n':
        return {"error": "Not a valid PNG file"}
    
    # Extract width and height from IHDR chunk
    width = int.from_bytes(png_data[16:20], byteorder='big')
    height = int.from_bytes(png_data[20:24], byteorder='big')
    
    return {
        "width": width,
        "height": height,
        "file_size": len(png_data),
        "valid": True
    }


def measure_performance(func: Callable) -> Callable:
    """Decorator to measure function performance."""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        start_memory = get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.perf_counter()
            end_memory = get_memory_usage()
            
            performance_data = {
                "execution_time": end_time - start_time,
                "memory_delta": end_memory - start_memory,
                "peak_memory": end_memory
            }
            
            # Store performance data on result if possible
            if hasattr(result, '__dict__'):
                result._performance = performance_data
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            end_memory = get_memory_usage()
            
            # Still record timing for failed operations
            e._performance = {
                "execution_time": end_time - start_time,
                "memory_delta": end_memory - start_memory,
                "peak_memory": end_memory,
                "failed": True
            }
            raise
    
    return wrapper


def measure_async_performance(func: Callable) -> Callable:
    """Decorator to measure async function performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        start_memory = get_memory_usage()
        
        try:
            result = await func(*args, **kwargs)
            
            end_time = time.perf_counter()
            end_memory = get_memory_usage()
            
            performance_data = {
                "execution_time": end_time - start_time,
                "memory_delta": end_memory - start_memory,
                "peak_memory": end_memory
            }
            
            # Store performance data on result if possible
            if hasattr(result, '__dict__'):
                result._performance = performance_data
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            end_memory = get_memory_usage()
            
            # Still record timing for failed operations
            e._performance = {
                "execution_time": end_time - start_time,
                "memory_delta": end_memory - start_memory,
                "peak_memory": end_memory,
                "failed": True
            }
            raise
    
    return wrapper


def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except Exception:
        return 0.0


def get_system_info() -> Dict[str, Any]:
    """Get system information for test environment."""
    try:
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
            "memory_available": psutil.virtual_memory().available / 1024 / 1024 / 1024,  # GB
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.sys.platform
        }
    except Exception:
        return {"error": "Could not gather system info"}


class MockEnvironment:
    """Context manager for mocking environment variables."""
    
    def __init__(self, env_vars: Dict[str, str]):
        self.env_vars = env_vars
        self.original_values = {}
    
    def __enter__(self):
        for key, value in self.env_vars.items():
            self.original_values[key] = os.environ.get(key)
            os.environ[key] = value
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.env_vars:
            if self.original_values[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self.original_values[key]


class ConcurrentExecutor:
    """Helper for running concurrent tests."""
    
    @staticmethod
    async def run_concurrent_tasks(tasks: List[Callable], max_concurrent: int = 10) -> List[Any]:
        """Run tasks concurrently with limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                if asyncio.iscoroutinefunction(task):
                    return await task()
                else:
                    return task()
        
        return await asyncio.gather(*[run_with_semaphore(task) for task in tasks])
    
    @staticmethod
    async def stress_test_endpoint(
        endpoint_func: Callable,
        args_list: List[tuple],
        concurrent_requests: int = 10,
        total_requests: int = 100
    ) -> Dict[str, Any]:
        """Stress test an endpoint with concurrent requests."""
        results = []
        errors = []
        start_time = time.perf_counter()
        
        async def make_request(args):
            try:
                result = await endpoint_func(*args)
                results.append(result)
                return result
            except Exception as e:
                errors.append(str(e))
                raise
        
        # Create request tasks
        tasks = []
        for i in range(total_requests):
            args = args_list[i % len(args_list)]
            tasks.append(lambda a=args: make_request(a))
        
        # Run with concurrency limit
        await ConcurrentExecutor.run_concurrent_tasks(tasks, concurrent_requests)
        
        end_time = time.perf_counter()
        
        return {
            "total_requests": total_requests,
            "concurrent_requests": concurrent_requests,
            "successful_requests": len(results),
            "failed_requests": len(errors),
            "total_time": end_time - start_time,
            "requests_per_second": total_requests / (end_time - start_time),
            "errors": errors[:10]  # First 10 errors
        }


def create_test_png_file(width: int = 100, height: int = 100) -> bytes:
    """Create a minimal valid PNG file for testing."""
    # This creates a minimal PNG file - for real testing you might want to use PIL
    # This is a simplified version
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = (
        width.to_bytes(4, 'big') +
        height.to_bytes(4, 'big') +
        b'\x08\x02\x00\x00\x00'  # bit depth, color type, compression, filter, interlace
    )
    ihdr_crc = 0  # Simplified - real PNG needs proper CRC
    ihdr_chunk = (
        len(ihdr_data).to_bytes(4, 'big') +
        b'IHDR' +
        ihdr_data +
        ihdr_crc.to_bytes(4, 'big')
    )
    
    # IEND chunk
    iend_chunk = b'\x00\x00\x00\x00IEND\xae\x42\x60\x82'
    
    return png_signature + ihdr_chunk + iend_chunk


class DatabaseHelper:
    """Helper for database operations in tests."""
    
    @staticmethod
    async def clear_redis(redis_client) -> None:
        """Clear Redis database."""
        await redis_client.flushdb()
    
    @staticmethod
    async def setup_test_data(redis_client, test_data: Dict[str, Any]) -> None:
        """Setup test data in Redis."""
        for key, value in test_data.items():
            if isinstance(value, dict):
                await redis_client.hset(key, mapping=value)
            else:
                await redis_client.set(key, value)
    
    @staticmethod
    async def verify_redis_data(redis_client, expected_data: Dict[str, Any]) -> List[str]:
        """Verify Redis data matches expected."""
        errors = []
        
        for key, expected_value in expected_data.items():
            if isinstance(expected_value, dict):
                actual_value = await redis_client.hgetall(key)
                if actual_value != expected_value:
                    errors.append(f"Hash {key} mismatch: expected {expected_value}, got {actual_value}")
            else:
                actual_value = await redis_client.get(key)
                if actual_value != expected_value:
                    errors.append(f"Key {key} mismatch: expected {expected_value}, got {actual_value}")
        
        return errors


def patch_async_function(target: str, return_value: Any = None, side_effect: Any = None):
    """Helper to patch async functions."""
    mock = AsyncMock(return_value=return_value, side_effect=side_effect)
    return patch(target, mock)


class TestTimer:
    """Context manager for timing test operations."""
    
    def __init__(self, description: str = ""):
        self.description = description
        self.start_time = 0
        self.end_time = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        print(f"⏱️  {self.description}: {duration:.3f}s")
    
    @property
    def duration(self) -> float:
        """Get the measured duration."""
        return self.end_time - self.start_time


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry failed operations."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def generate_test_report(test_results: List[Dict[str, Any]]) -> str:
    """Generate a formatted test report."""
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result.get('passed', False))
    failed_tests = total_tests - passed_tests
    
    report_lines = [
        "=" * 60,
        "TEST REPORT",
        "=" * 60,
        f"Total Tests: {total_tests}",
        f"Passed: {passed_tests}",
        f"Failed: {failed_tests}",
        f"Success Rate: {(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "No tests",
        "=" * 60,
        ""
    ]
    
    if failed_tests > 0:
        report_lines.extend(["FAILED TESTS:", "-" * 20])
        for result in test_results:
            if not result.get('passed', False):
                report_lines.append(f"❌ {result.get('name', 'Unknown')}: {result.get('error', 'Unknown error')}")
        report_lines.append("")
    
    if passed_tests > 0:
        report_lines.extend(["PASSED TESTS:", "-" * 20])
        for result in test_results:
            if result.get('passed', False):
                duration = result.get('duration', 0)
                report_lines.append(f"✅ {result.get('name', 'Unknown')}: {duration:.3f}s")
    
    return "\n".join(report_lines)