"""
Unit Tests for Storage Manager
==============================

Comprehensive unit tests for the 3-tier file storage system, caching, and cleanup operations.
"""

import pytest
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, mock_open
from typing import Dict, Any, Optional

from src.core.storage.manager import (
    StorageError, FileMetadata, StorageTier, FileStorageManager,
    get_storage_manager, close_storage_manager
)
from src.models.schemas import PNGResult

from tests.utils.assertions import assert_valid_png_result
from tests.utils.data_generators import MockDataGenerator
from tests.utils.helpers import create_temp_directory, measure_performance, TestTimer


class TestStorageError:
    """Test storage error handling."""
    
    def test_storage_error_creation(self):
        """Test creating storage error."""
        error = StorageError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_storage_error_inheritance(self):
        """Test error inheritance."""
        error = StorageError("Test")
        assert isinstance(error, Exception)


class TestFileMetadata:
    """Test file metadata class."""
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample file metadata."""
        return FileMetadata(
            file_path=Path("/test/path/file.png"),
            content_hash="abc123def456",
            file_size=1024,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            last_accessed=datetime(2023, 1, 2, 12, 0, 0),
            metadata={"task_id": "test-task", "width": 800, "height": 600}
        )
    
    def test_metadata_initialization(self, sample_metadata):
        """Test metadata initialization."""
        assert sample_metadata.file_path == Path("/test/path/file.png")
        assert sample_metadata.content_hash == "abc123def456"
        assert sample_metadata.file_size == 1024
        assert sample_metadata.created_at == datetime(2023, 1, 1, 12, 0, 0)
        assert sample_metadata.last_accessed == datetime(2023, 1, 2, 12, 0, 0)
        assert sample_metadata.access_count == 1
        assert sample_metadata.metadata["task_id"] == "test-task"
    
    def test_metadata_to_dict(self, sample_metadata):
        """Test metadata serialization."""
        data = sample_metadata.to_dict()
        
        assert data["file_path"] == "/test/path/file.png"
        assert data["content_hash"] == "abc123def456"
        assert data["file_size"] == 1024
        assert data["created_at"] == "2023-01-01T12:00:00"
        assert data["last_accessed"] == "2023-01-02T12:00:00"
        assert data["access_count"] == 1
        assert data["metadata"]["task_id"] == "test-task"
    
    def test_metadata_from_dict(self, sample_metadata):
        """Test metadata deserialization."""
        data = sample_metadata.to_dict()
        restored = FileMetadata.from_dict(data)
        
        assert restored.file_path == sample_metadata.file_path
        assert restored.content_hash == sample_metadata.content_hash
        assert restored.file_size == sample_metadata.file_size
        assert restored.created_at == sample_metadata.created_at
        assert restored.last_accessed == sample_metadata.last_accessed
        assert restored.access_count == sample_metadata.access_count
        assert restored.metadata == sample_metadata.metadata
    
    def test_metadata_from_dict_minimal(self):
        """Test metadata deserialization with minimal data."""
        data = {
            "file_path": "/test/file.png",
            "content_hash": "hash123",
            "file_size": 512,
            "created_at": "2023-01-01T00:00:00",
            "last_accessed": "2023-01-01T00:00:00"
        }
        
        metadata = FileMetadata.from_dict(data)
        
        assert metadata.file_path == Path("/test/file.png")
        assert metadata.content_hash == "hash123"
        assert metadata.file_size == 512
        assert metadata.access_count == 1  # Default value
        assert metadata.metadata == {}  # Default empty dict


class TestStorageTier:
    """Test storage tier management."""
    
    @pytest.fixture
    def temp_storage_path(self):
        """Create temporary storage path."""
        return create_temp_directory()
    
    @pytest.fixture
    def storage_tier(self, temp_storage_path):
        """Create storage tier instance."""
        return StorageTier(
            name="test_tier",
            base_path=temp_storage_path / "test_tier",
            max_size_mb=100,
            retention_days=7,
            cleanup_threshold=0.8
        )
    
    def test_storage_tier_initialization(self, storage_tier, temp_storage_path):
        """Test storage tier initialization."""
        assert storage_tier.name == "test_tier"
        assert storage_tier.base_path == temp_storage_path / "test_tier"
        assert storage_tier.max_size_mb == 100
        assert storage_tier.retention_days == 7
        assert storage_tier.cleanup_threshold == 0.8
        assert storage_tier.logger is not None
        
        # Directory should be created
        assert storage_tier.base_path.exists()
        assert storage_tier.base_path.is_dir()
    
    @pytest.mark.asyncio
    async def test_get_size_mb_empty(self, storage_tier):
        """Test getting size of empty tier."""
        size = await storage_tier.get_size_mb()
        assert size == 0.0
    
    @pytest.mark.asyncio
    async def test_get_size_mb_with_files(self, storage_tier):
        """Test getting size with files."""
        # Create test files
        test_file1 = storage_tier.base_path / "file1.png"
        test_file2 = storage_tier.base_path / "file2.png"
        
        test_file1.write_bytes(b"x" * 1024)  # 1KB
        test_file2.write_bytes(b"y" * 2048)  # 2KB
        
        size = await storage_tier.get_size_mb()
        expected_size = 3072 / (1024 * 1024)  # 3KB in MB
        assert abs(size - expected_size) < 0.001
    
    @pytest.mark.asyncio
    async def test_get_size_mb_nonexistent_path(self):
        """Test getting size of nonexistent path."""
        tier = StorageTier(
            name="nonexistent",
            base_path=Path("/nonexistent/path"),
            max_size_mb=100,
            retention_days=7
        )
        # Don't create the directory
        tier.base_path.rmdir()
        
        size = await tier.get_size_mb()
        assert size == 0.0
    
    @pytest.mark.asyncio
    async def test_needs_cleanup_under_threshold(self, storage_tier):
        """Test cleanup check when under threshold."""
        # Empty tier should not need cleanup
        needs_cleanup = await storage_tier.needs_cleanup()
        assert needs_cleanup is False
    
    @pytest.mark.asyncio
    async def test_needs_cleanup_over_threshold(self, storage_tier):
        """Test cleanup check when over threshold."""
        # Create enough files to exceed threshold
        large_file = storage_tier.base_path / "large.png"
        large_file.write_bytes(b"x" * (85 * 1024 * 1024))  # 85MB (over 80% of 100MB)
        
        needs_cleanup = await storage_tier.needs_cleanup()
        assert needs_cleanup is True
    
    def test_get_date_path(self, storage_tier):
        """Test date-based path generation."""
        test_date = datetime(2023, 5, 15, 10, 30, 45)
        date_path = storage_tier.get_date_path(test_date)
        
        expected_path = storage_tier.base_path / "2023/05/15"
        assert date_path == expected_path
    
    def test_get_file_path(self, storage_tier):
        """Test file path generation."""
        content_hash = "abc123def456789"
        
        with patch('src.core.storage.manager.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2023, 5, 15, 10, 30, 45)
            
            file_path = storage_tier.get_file_path(content_hash)
            
            expected_path = (storage_tier.base_path / "2023/05/15" / "ab" / f"{content_hash}.png")
            assert file_path == expected_path
    
    def test_get_file_path_custom_extension(self, storage_tier):
        """Test file path generation with custom extension."""
        content_hash = "xyz789"
        file_path = storage_tier.get_file_path(content_hash, ".jpg")
        
        assert file_path.suffix == ".jpg"
        assert content_hash in str(file_path)


class TestFileStorageManager:
    """Test file storage manager."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.storage_path = Path("/tmp/test_storage")
        settings.cache_ttl = 3600
        return settings
    
    @pytest.fixture(autouse=True)
    def mock_redis(self):
        """Create mock Redis client with proper async context manager protocol."""
        redis = AsyncMock()
        redis.hset = AsyncMock()
        redis.hgetall = AsyncMock()
        redis.setex = AsyncMock()
        redis.get = AsyncMock()
        redis.delete = AsyncMock()
        redis.keys = AsyncMock()
        redis.expire = AsyncMock()
        
        # Create proper async context manager
        class AsyncContextManagerMock:
            def __init__(self, redis_mock):
                self.redis_mock = redis_mock
            
            async def __aenter__(self):
                return self.redis_mock
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        context_manager = AsyncContextManagerMock(redis)
        
        # Create async function that returns the context manager
        async def mock_get_redis_client():
            return context_manager
        
        # Patch get_redis_client to return an awaitable that yields the context manager
        with patch('src.core.storage.manager.get_redis_client', side_effect=mock_get_redis_client):
            yield redis
    
    @pytest.fixture
    def storage_manager(self, mock_settings):
        """Create storage manager instance."""
        with patch('src.core.storage.manager.get_settings', return_value=mock_settings):
            return FileStorageManager()
    
    @pytest.fixture
    def sample_png_result(self):
        """Create sample PNG result."""
        return MockDataGenerator.generate_png_result()
    
    def test_storage_manager_initialization(self, storage_manager, mock_settings):
        """Test storage manager initialization."""
        assert storage_manager.settings == mock_settings
        assert storage_manager.logger is not None
        assert 'hot' in storage_manager.tiers
        assert 'warm' in storage_manager.tiers
        assert storage_manager.redis_cache_ttl == 3600
        assert storage_manager.content_hash_cache == {}
        assert storage_manager._cleanup_task is None
        assert storage_manager._running is False
    
    def test_storage_tiers_configuration(self, storage_manager):
        """Test storage tiers are configured correctly."""
        hot_tier = storage_manager.tiers['hot']
        warm_tier = storage_manager.tiers['warm']
        
        assert hot_tier.name == 'hot'
        assert hot_tier.max_size_mb == 500
        assert hot_tier.retention_days == 7
        assert hot_tier.cleanup_threshold == 0.8
        
        assert warm_tier.name == 'warm'
        assert warm_tier.max_size_mb == 2000
        assert warm_tier.retention_days == 30
        assert warm_tier.cleanup_threshold == 0.9
    
    @pytest.mark.asyncio
    async def test_initialize_storage_manager(self, storage_manager):
        """Test storage manager initialization."""
        with patch.object(storage_manager, '_periodic_cleanup') as mock_cleanup:
            await storage_manager.initialize()
            
            assert storage_manager._running is True
            assert storage_manager._cleanup_task is not None
    
    @pytest.mark.asyncio
    async def test_close_storage_manager(self, storage_manager):
        """Test storage manager closing."""
        # Setup running state
        storage_manager._running = True
        
        # Create a real asyncio.Task that can be cancelled and awaited
        async def dummy_task():
            await asyncio.sleep(1)  # This will be cancelled
        
        # Create a real task
        cleanup_task = asyncio.create_task(dummy_task())
        storage_manager._cleanup_task = cleanup_task
        
        await storage_manager.close()
        
        assert storage_manager._running is False
        assert cleanup_task.cancelled()
    
    def test_calculate_content_hash(self, storage_manager):
        """Test content hash calculation."""
        test_data = b"test data for hashing"
        expected_hash = hashlib.sha256(test_data).hexdigest()
        
        calculated_hash = storage_manager._calculate_content_hash(test_data)
        assert calculated_hash == expected_hash
    
    @pytest.mark.asyncio
    async def test_store_png_new_file(self, storage_manager, sample_png_result, mock_redis):
        """Test storing new PNG file."""
        content_hash = "abc123def456"
        task_id = "test-task-123"
        
        with patch.object(storage_manager, '_calculate_content_hash', return_value=content_hash):
            with patch.object(storage_manager, '_find_existing_file', return_value=None):
                with patch.object(storage_manager, '_store_in_tier') as mock_store:
                    with patch.object(storage_manager, '_store_file_metadata') as mock_meta:
                        with patch.object(storage_manager, '_cache_file_reference') as mock_cache:
                            test_path = Path("/test/path/file.png")
                            mock_store.return_value = test_path
                            
                            result_hash = await storage_manager.store_png(sample_png_result, task_id)
                            
                            assert result_hash == content_hash
                            mock_store.assert_called_once_with('hot', content_hash, sample_png_result)
                            mock_meta.assert_called_once()
                            mock_cache.assert_called_once_with(content_hash, test_path)
    
    @pytest.mark.asyncio
    async def test_store_png_existing_file(self, storage_manager, sample_png_result):
        """Test storing PNG file that already exists (deduplication)."""
        content_hash = "existing123"
        existing_path = Path("/existing/file.png")
        
        with patch.object(storage_manager, '_calculate_content_hash', return_value=content_hash):
            with patch.object(storage_manager, '_find_existing_file', return_value=existing_path):
                with patch.object(storage_manager, '_update_file_metadata') as mock_update:
                    with patch.object(storage_manager, '_cache_file_reference') as mock_cache:
                        
                        result_hash = await storage_manager.store_png(sample_png_result)
                        
                        assert result_hash == content_hash
                        mock_update.assert_called_once_with(content_hash, existing_path)
                        mock_cache.assert_called_once_with(content_hash, existing_path)
    
    @pytest.mark.asyncio
    async def test_store_png_error_handling(self, storage_manager, sample_png_result):
        """Test PNG storage error handling."""
        with patch.object(storage_manager, '_calculate_content_hash', side_effect=Exception("Hash error")):
            with pytest.raises(StorageError, match="Failed to store PNG"):
                await storage_manager.store_png(sample_png_result)
    
    @pytest.mark.asyncio
    async def test_retrieve_png_from_cache(self, storage_manager):
        """Test retrieving PNG from cache."""
        content_hash = "cached123"
        cached_data = (b"cached_png_data", Mock())
        
        with patch.object(storage_manager, '_get_cached_file', return_value=cached_data):
            result = await storage_manager.retrieve_png(content_hash)
            
            assert result == cached_data
    
    @pytest.mark.asyncio
    async def test_retrieve_png_from_storage(self, storage_manager):
        """Test retrieving PNG from storage."""
        content_hash = "storage123"
        file_path = Path("/storage/file.png")
        png_data = b"stored_png_data"
        
        # Create metadata mock with proper access_count attribute
        metadata = Mock()
        metadata.access_count = 1
        
        with patch.object(storage_manager, '_get_cached_file', return_value=None):
            with patch.object(storage_manager, '_find_existing_file', return_value=file_path):
                # Create proper async context manager mock for aiofiles.open
                mock_file = AsyncMock()
                mock_file.__aenter__ = AsyncMock(return_value=mock_file)
                mock_file.__aexit__ = AsyncMock(return_value=None)
                mock_file.read = AsyncMock(return_value=png_data)
                
                with patch('aiofiles.open', return_value=mock_file):
                    with patch.object(storage_manager, '_get_file_metadata', return_value=metadata):
                        with patch.object(storage_manager, '_store_file_metadata') as mock_store_meta:
                            with patch.object(storage_manager, '_cache_file_data') as mock_cache:
                                
                                result = await storage_manager.retrieve_png(content_hash)
                                
                                assert result[0] == png_data
                                assert result[1] == metadata
                                assert metadata.access_count == 2  # Incremented
                                mock_store_meta.assert_called_once()
                                mock_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_png_not_found(self, storage_manager):
        """Test retrieving non-existent PNG."""
        content_hash = "notfound123"
        
        with patch.object(storage_manager, '_get_cached_file', return_value=None):
            with patch.object(storage_manager, '_find_existing_file', return_value=None):
                result = await storage_manager.retrieve_png(content_hash)
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_retrieve_png_error_handling(self, storage_manager):
        """Test PNG retrieval error handling."""
        content_hash = "error123"
        
        with patch.object(storage_manager, '_get_cached_file', side_effect=Exception("Cache error")):
            with pytest.raises(StorageError, match="Failed to retrieve PNG"):
                await storage_manager.retrieve_png(content_hash)
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage_manager):
        """Test successful file deletion."""
        content_hash = "delete123"
        file_path = Path("/test/delete.png")
        
        with patch.object(storage_manager, '_find_existing_file', return_value=file_path):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('aiofiles.os.remove') as mock_remove:
                    with patch.object(storage_manager, '_cleanup_empty_directories') as mock_cleanup:
                        with patch.object(storage_manager, '_delete_file_metadata') as mock_del_meta:
                            with patch.object(storage_manager, '_remove_from_cache') as mock_cache:
                                
                                result = await storage_manager.delete_file(content_hash)
                                
                                assert result is True
                                mock_remove.assert_called_once_with(file_path)
                                mock_cleanup.assert_called_once_with(file_path.parent)
                                mock_del_meta.assert_called_once_with(content_hash)
                                mock_cache.assert_called_once_with(content_hash)
    
    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, storage_manager):
        """Test deleting non-existent file."""
        content_hash = "notfound123"
        
        with patch.object(storage_manager, '_find_existing_file', return_value=None):
            with patch.object(storage_manager, '_delete_file_metadata') as mock_del_meta:
                with patch.object(storage_manager, '_remove_from_cache') as mock_cache:
                    
                    result = await storage_manager.delete_file(content_hash)
                    
                    assert result is True
                    mock_del_meta.assert_called_once()
                    mock_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_file_error_handling(self, storage_manager):
        """Test file deletion error handling."""
        content_hash = "error123"
        
        with patch.object(storage_manager, '_find_existing_file', side_effect=Exception("Find error")):
            result = await storage_manager.delete_file(content_hash)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, storage_manager, mock_redis):
        """Test getting storage statistics."""
        # Mock tier statistics
        with patch.object(storage_manager.tiers['hot'], 'get_size_mb', return_value=250.5):
            with patch.object(storage_manager.tiers['warm'], 'get_size_mb', return_value=1500.0):
                with patch.object(storage_manager, '_count_files_in_tier', side_effect=[100, 500]):
                    # Use the existing mock_redis fixture - don't override the patch
                    mock_redis.keys.return_value = ['file:1', 'file:2', 'file:3']
                    
                    stats = await storage_manager.get_storage_stats()
                    
                    assert stats['total_files'] == 600
                    assert stats['total_size_mb'] == 1750.5
                    
                    # Check hot tier stats
                    hot_stats = stats['tiers']['hot']
                    assert hot_stats['size_mb'] == 250.5
                    assert hot_stats['max_size_mb'] == 500
                    assert hot_stats['utilization'] == 0.501
                    assert hot_stats['file_count'] == 100
                    
                    # Check cache stats
                    assert stats['cache_stats']['cached_files'] == 3
    
    @pytest.mark.asyncio
    async def test_get_storage_stats_redis_error(self, storage_manager):
        """Test storage stats with Redis error."""
        with patch.object(storage_manager.tiers['hot'], 'get_size_mb', return_value=0):
            with patch.object(storage_manager.tiers['warm'], 'get_size_mb', return_value=0):
                with patch.object(storage_manager, '_count_files_in_tier', return_value=0):
                    with patch('src.core.storage.manager.get_redis_client', side_effect=Exception("Redis error")):
                        
                        stats = await storage_manager.get_storage_stats()
                        
                        assert 'error' in stats['cache_stats']
    
    @pytest.mark.asyncio
    async def test_find_existing_file_in_cache(self, storage_manager):
        """Test finding existing file from in-memory cache."""
        content_hash = "cached123"
        cached_path = Path("/cached/file.png")
        
        storage_manager.content_hash_cache[content_hash] = str(cached_path)
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await storage_manager._find_existing_file(content_hash)
            
            assert result == cached_path
    
    @pytest.mark.asyncio
    async def test_find_existing_file_in_tier(self, storage_manager):
        """Test finding existing file in storage tier."""
        content_hash = "tier123"
        tier_path = Path("/tier/file.png")
        
        with patch.object(storage_manager.tiers['hot'], 'get_file_path', return_value=tier_path):
            with patch('pathlib.Path.exists', return_value=True):
                result = await storage_manager._find_existing_file(content_hash)
                
                assert result == tier_path
                assert storage_manager.content_hash_cache[content_hash] == str(tier_path)
    
    @pytest.mark.asyncio
    async def test_find_existing_file_not_found(self, storage_manager):
        """Test finding non-existent file."""
        content_hash = "notfound123"
        
        with patch.object(storage_manager.tiers['hot'], 'get_file_path') as mock_hot_path:
            with patch.object(storage_manager.tiers['warm'], 'get_file_path') as mock_warm_path:
                mock_hot_path.return_value.exists.return_value = False
                mock_warm_path.return_value.exists.return_value = False
                
                result = await storage_manager._find_existing_file(content_hash)
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_store_in_tier(self, storage_manager, sample_png_result):
        """Test storing file in specific tier."""
        content_hash = "store123"
        tier_name = "hot"
        expected_path = Path("/hot/store/path.png")
        
        with patch.object(storage_manager.tiers[tier_name], 'get_file_path', return_value=expected_path):
            # Create proper async context manager mock
            mock_file = AsyncMock()
            mock_file.__aenter__ = AsyncMock(return_value=mock_file)
            mock_file.__aexit__ = AsyncMock(return_value=None)
            mock_file.write = AsyncMock()
            
            with patch('aiofiles.open', return_value=mock_file) as mock_open_func:
                result_path = await storage_manager._store_in_tier(tier_name, content_hash, sample_png_result)
                
                assert result_path == expected_path
                mock_open_func.assert_called_once_with(expected_path, 'wb')
    
    @pytest.mark.asyncio
    async def test_store_file_metadata_new(self, storage_manager, sample_png_result, mock_redis):
        """Test storing new file metadata."""
        content_hash = "meta123"
        file_path = Path("/test/meta.png")
        task_id = "task-123"
        
        # Use the mock_redis fixture which already has proper async context manager setup
        await storage_manager._store_file_metadata(content_hash, file_path, sample_png_result, task_id)
        
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_file_metadata_existing(self, storage_manager, mock_redis):
        """Test storing existing file metadata."""
        content_hash = "existing123"
        file_path = Path("/test/existing.png")
        existing_metadata = Mock()
        
        # Use the mock_redis fixture which already has proper async context manager setup
        await storage_manager._store_file_metadata(
            content_hash, file_path, None, None, existing_metadata
        )
        
        mock_redis.hset.assert_called_once()
        existing_metadata.to_dict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self, storage_manager, mock_redis):
        """Test getting file metadata successfully."""
        content_hash = "meta123"
        metadata_dict = {
            'file_path': '/test/file.png',
            'content_hash': content_hash,
            'file_size': 1024,
            'created_at': '2023-01-01T12:00:00',
            'last_accessed': '2023-01-01T12:00:00',
            'access_count': 5,
            'metadata': {'task_id': 'test'}
        }
        
        # Use the mock_redis fixture which already has proper async context manager setup
        mock_redis.hgetall.return_value = metadata_dict
        
        result = await storage_manager._get_file_metadata(content_hash)
        
        assert result is not None
        assert result.content_hash == content_hash
        assert result.file_size == 1024
        assert result.access_count == 5
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, storage_manager, mock_redis):
        """Test getting non-existent file metadata."""
        content_hash = "notfound123"
        
        # Use the mock_redis fixture which already has proper async context manager setup
        mock_redis.hgetall.return_value = None
        
        result = await storage_manager._get_file_metadata(content_hash)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_file_data_small_file(self, storage_manager, mock_redis):
        """Test caching small file data."""
        content_hash = "small123"
        data = b"small file data"  # < 1MB
        metadata = Mock()
        metadata.to_dict.return_value = {'test': 'metadata'}
        
        # Use the mock_redis fixture which already has proper async context manager setup
        await storage_manager._cache_file_data(content_hash, data, metadata)
        
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == f"file_data:{content_hash}"
        assert call_args[1] == storage_manager.redis_cache_ttl
    
    @pytest.mark.asyncio
    async def test_cache_file_data_large_file(self, storage_manager, mock_redis):
        """Test not caching large file data."""
        content_hash = "large123"
        data = b"x" * (2 * 1024 * 1024)  # 2MB > 1MB limit
        
        # Use the mock_redis fixture which already has proper async context manager setup
        await storage_manager._cache_file_data(content_hash, data, None)
        
        # Should not cache large files
        mock_redis.setex.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_cached_file_success(self, storage_manager, mock_redis):
        """Test getting cached file data successfully."""
        content_hash = "cached123"
        cached_data = {
            'data': b"test data".hex(),
            'metadata': {'file_path': '/test/file.png', 'content_hash': content_hash,
                        'file_size': 9, 'created_at': '2023-01-01T00:00:00',
                        'last_accessed': '2023-01-01T00:00:00'}
        }
        
        # Use the mock_redis fixture which already has proper async context manager setup
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await storage_manager._get_cached_file(content_hash)
        
        assert result is not None
        assert result[0] == b"test data"
        assert result[1] is not None
    
    @pytest.mark.asyncio
    async def test_get_cached_file_not_found(self, storage_manager, mock_redis):
        """Test getting non-existent cached file."""
        content_hash = "notcached123"
        
        # Use the mock_redis fixture which already has proper async context manager setup
        mock_redis.get.return_value = None
        
        result = await storage_manager._get_cached_file(content_hash)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_count_files_in_tier(self, storage_manager):
        """Test counting files in storage tier."""
        tier_name = "hot"
        tier = storage_manager.tiers[tier_name]
        
        # Create mock files
        mock_files = [
            Mock(is_file=Mock(return_value=True)),
            Mock(is_file=Mock(return_value=True)),
            Mock(is_file=Mock(return_value=False)),  # Directory
        ]
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.rglob', return_value=mock_files):
                count = await storage_manager._count_files_in_tier(tier_name)
                
                assert count == 2  # Only actual files
    
    @pytest.mark.asyncio
    async def test_count_files_in_nonexistent_tier(self, storage_manager):
        """Test counting files in non-existent tier path."""
        tier_name = "hot"
        tier = storage_manager.tiers[tier_name]
        
        with patch('pathlib.Path.exists', return_value=False):
            count = await storage_manager._count_files_in_tier(tier_name)
            
            assert count == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_empty_directories(self, storage_manager):
        """Test cleaning up empty directories."""
        test_dir = Path("/test/empty/nested/dir")
        
        # Mock the pathlib.Path methods at the module level
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_dir', return_value=True):
                with patch('pathlib.Path.iterdir', return_value=iter([])):  # Empty directory
                    with patch('pathlib.Path.rmdir') as mock_rmdir:
                        
                        await storage_manager._cleanup_empty_directories(test_dir)
                        
                        # Verify rmdir was called (may be called multiple times for recursive cleanup)
                        assert mock_rmdir.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_perform_cleanup(self, storage_manager):
        """Test performing storage cleanup."""
        hot_tier = storage_manager.tiers['hot']
        warm_tier = storage_manager.tiers['warm']
        
        with patch.object(hot_tier, 'needs_cleanup', return_value=True):
            with patch.object(warm_tier, 'needs_cleanup', return_value=False):
                with patch.object(storage_manager, '_cleanup_tier') as mock_cleanup_tier:
                    with patch.object(storage_manager, '_cleanup_expired_files') as mock_cleanup_expired:
                        
                        await storage_manager._perform_cleanup()
                        
                        # Should cleanup hot tier but not warm tier
                        mock_cleanup_tier.assert_called_once_with('hot', hot_tier)
                        
                        # Should cleanup expired files for both tiers
                        assert mock_cleanup_expired.call_count == 2


class TestGlobalStorageManagerFunctions:
    """Test global storage manager functions."""
    
    @pytest.mark.asyncio
    async def test_get_storage_manager_new(self):
        """Test getting new global storage manager."""
        with patch('src.core.storage.manager._global_storage_manager', None):
            with patch('src.core.storage.manager.FileStorageManager') as mock_manager_class:
                mock_manager = AsyncMock()
                mock_manager_class.return_value = mock_manager
                
                manager = await get_storage_manager()
                
                assert manager == mock_manager
                mock_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_storage_manager_existing(self):
        """Test getting existing global storage manager."""
        mock_existing = Mock()
        
        with patch('src.core.storage.manager._global_storage_manager', mock_existing):
            manager = await get_storage_manager()
            
            assert manager == mock_existing
    
    @pytest.mark.asyncio
    async def test_close_storage_manager_existing(self):
        """Test closing existing global storage manager."""
        mock_manager = AsyncMock()
        
        with patch('src.core.storage.manager._global_storage_manager', mock_manager):
            await close_storage_manager()
            
            mock_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_storage_manager_none(self):
        """Test closing when no global storage manager exists."""
        with patch('src.core.storage.manager._global_storage_manager', None):
            # Should not raise error
            await close_storage_manager()


class TestStorageManagerPerformance:
    """Test storage manager performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_store_retrieve_performance(self):
        """Test store and retrieve performance."""
        png_result = MockDataGenerator.generate_png_result()
        
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            
            # Mock all I/O operations for performance test
            with patch.object(manager, '_find_existing_file', return_value=None):
                with patch.object(manager, '_store_in_tier', return_value=Path("/test/file.png")):
                    with patch.object(manager, '_store_file_metadata'):
                        with patch.object(manager, '_cache_file_reference'):
                            
                            with TestTimer() as timer:
                                content_hash = await manager.store_png(png_result)
                            
                            assert timer.duration < 0.1  # Should be fast with mocks
                            assert content_hash is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent storage operations."""
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            
            # Mock operations
            with patch.object(manager, '_find_existing_file', return_value=None):
                with patch.object(manager, '_store_in_tier', return_value=Path("/test/file.png")):
                    with patch.object(manager, '_store_file_metadata'):
                        with patch.object(manager, '_cache_file_reference'):
                            
                            async def store_operation(i):
                                png_result = MockDataGenerator.generate_png_result()
                                return await manager.store_png(png_result, f"task-{i}")
                            
                            # Run 10 concurrent operations
                            tasks = [store_operation(i) for i in range(10)]
                            
                            with TestTimer() as timer:
                                results = await asyncio.gather(*tasks)
                            
                            assert len(results) == 10
                            assert all(hash_val for hash_val in results)
                            assert timer.duration < 1.0  # Should complete quickly


class TestStorageManagerEdgeCases:
    """Test storage manager edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_store_png_with_unicode_metadata(self):
        """Test storing PNG with unicode metadata."""
        png_result = MockDataGenerator.generate_png_result()
        png_result.metadata['unicode_text'] = "测试文档 🌍"
        
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            
            with patch.object(manager, '_find_existing_file', return_value=None):
                with patch.object(manager, '_store_in_tier', return_value=Path("/test/unicode.png")):
                    with patch.object(manager, '_store_file_metadata') as mock_meta:
                        with patch.object(manager, '_cache_file_reference'):
                            
                            content_hash = await manager.store_png(png_result)
                            
                            assert content_hash is not None
                            mock_meta.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_png_corrupted_cache_data(self):
        """Test retrieving PNG with corrupted cache data."""
        content_hash = "corrupted123"
        
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            
            with patch.object(manager, '_get_cached_file', side_effect=Exception("Corrupted cache")):
                with patch.object(manager, '_find_existing_file', return_value=None):
                    
                    with pytest.raises(StorageError):
                        await manager.retrieve_png(content_hash)
    
    @pytest.mark.asyncio
    async def test_cleanup_with_permission_errors(self):
        """Test cleanup with file permission errors."""
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            tier = manager.tiers['hot']
            
            # Mock files that can't be deleted
            mock_files = [Mock()]
            mock_files[0].is_file.return_value = True
            mock_files[0].stat.return_value = Mock(st_atime=0, st_size=1024)
            
            with patch.object(tier.base_path, 'rglob', return_value=mock_files):
                with patch.object(tier, 'get_size_mb', side_effect=[100, 80]):  # Over threshold, then under
                    with patch('aiofiles.os.remove', side_effect=PermissionError("Permission denied")):
                        
                        # Should not raise error, just log warning
                        await manager._cleanup_tier('hot', tier)
    
    @pytest.mark.asyncio
    async def test_find_existing_file_in_old_directories(self):
        """Test finding files in old date directories."""
        content_hash = "old123"
        
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            tier = manager.tiers['hot']
            
            # Mock current path doesn't exist, but old path does
            current_path = Mock()
            current_path.exists.return_value = False
            
            old_path = Mock()
            old_path.exists.return_value = True
            
            with patch.object(tier, 'get_file_path', return_value=current_path):
                with patch.object(tier, 'get_date_path') as mock_date_path:
                    # Create a mock that supports path division operations
                    mock_base_path = Mock()
                    mock_hash_path = Mock()
                    mock_hash_path.return_value = old_path
                    mock_base_path.__truediv__ = Mock(return_value=mock_hash_path)
                    mock_hash_path.__truediv__ = mock_hash_path
                    mock_date_path.return_value = mock_base_path
                    
                    result = await manager._find_existing_file(content_hash)
                    
                    assert result == old_path
                    assert manager.content_hash_cache[content_hash] == str(old_path)
    
    def test_storage_tier_with_invalid_path(self):
        """Test storage tier with invalid path characters."""
        # Test with path that might cause issues on some systems
        problematic_path = Path("/test/with spaces/and:colons")
        
        tier = StorageTier(
            name="problematic",
            base_path=problematic_path,
            max_size_mb=100,
            retention_days=7
        )
        
        # Should handle gracefully
        assert tier.base_path == problematic_path
        assert tier.name == "problematic"
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self):
        """Test handling Redis connection failures."""
        with patch('src.core.storage.manager.get_settings'):
            manager = FileStorageManager()
            
            # Create async context manager mock that raises exception
            async_context_mock = AsyncMock()
            async_context_mock.__aenter__ = AsyncMock(side_effect=Exception("Redis unavailable"))
            async_context_mock.__aexit__ = AsyncMock(return_value=None)
            
            with patch('src.core.storage.manager.get_redis_client', return_value=async_context_mock):
                # Should not fail completely, just skip Redis operations
                metadata = await manager._get_file_metadata("test123")
                assert metadata is None
    
    @pytest.mark.asyncio
    async def test_file_metadata_with_missing_fields(self):
        """Test file metadata handling with missing fields."""
        incomplete_data = {
            'file_path': '/test/file.png',
            'content_hash': 'test123',
            'file_size': 1024,
            'created_at': '2023-01-01T00:00:00',
            'last_accessed': '2023-01-01T00:00:00'
            # Missing access_count and metadata fields
        }
        
        metadata = FileMetadata.from_dict(incomplete_data)
        
        assert metadata.access_count == 1  # Default value
        assert metadata.metadata == {}  # Default empty dict
        assert metadata.file_path == Path('/test/file.png')