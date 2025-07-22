"""
Unit Tests for PNG Generator
============================

Comprehensive unit tests for PNG generation, browser pool management, and image optimization.
"""

import pytest
import asyncio
import base64
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from src.core.rendering.png_generator import (
    PNGGenerationError, BrowserPool, PlaywrightPNGGenerator,
    AdvancedPNGGenerator, PNGGeneratorFactory,
    initialize_browser_pool, close_browser_pool, generate_png_from_html
)
from src.models.schemas import RenderOptions, PNGResult

from tests.utils.assertions import (
    assert_valid_png_result, assert_performance_within_threshold
)
from tests.utils.data_generators import RenderOptionsGenerator
from tests.utils.helpers import TestTimer


class TestPNGGenerationError:
    """Test PNG generation error handling."""
    
    def test_png_generation_error_creation(self):
        """Test creating PNG generation error."""
        error = PNGGenerationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_png_generation_error_inheritance(self):
        """Test error inheritance."""
        error = PNGGenerationError("Test")
        assert isinstance(error, Exception)


class TestBrowserPool:
    """Test browser pool management."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.playwright_headless = True
        settings.browser_pool_size = 3  # Ensure this returns an integer, not MagicMock
        settings.playwright_timeout = 30000
        return settings
    
    @pytest.fixture
    def browser_pool(self, mock_settings):
        """Create browser pool instance."""
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            return BrowserPool(pool_size=2)
    
    def test_browser_pool_initialization(self, browser_pool):
        """Test browser pool initialization."""
        assert browser_pool.pool_size == 2
        assert browser_pool.browsers == []
        assert browser_pool._playwright is None
        assert browser_pool._semaphore._value == 2
        assert browser_pool.settings is not None
        assert browser_pool.logger is not None
    
    @pytest.mark.asyncio
    async def test_initialize_browser_pool_success(self, browser_pool):
        """Test successful browser pool initialization."""
        # Mock playwright components
        mock_browser = AsyncMock()
        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser
        mock_playwright = AsyncMock()
        mock_playwright.chromium = mock_chromium
        
        with patch('src.core.rendering.png_generator.async_playwright') as mock_async_playwright:
            # Configure AsyncMock to be awaitable
            mock_async_playwright_instance = AsyncMock()
            mock_async_playwright_instance.start = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value = mock_async_playwright_instance
            
            await browser_pool.initialize()
            
            assert len(browser_pool.browsers) == 2
            assert browser_pool._playwright == mock_playwright
            assert mock_chromium.launch.call_count == 2
    
    @pytest.mark.asyncio
    async def test_initialize_browser_pool_failure(self, browser_pool):
        """Test browser pool initialization failure."""
        with patch('src.core.rendering.png_generator.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start.side_effect = Exception("Playwright failed")
            
            with pytest.raises(PNGGenerationError, match="Browser pool initialization failed"):
                await browser_pool.initialize()
    
    @pytest.mark.asyncio
    async def test_close_browser_pool(self, browser_pool):
        """Test closing browser pool."""
        # Setup browsers
        mock_browser1 = AsyncMock()
        mock_browser2 = AsyncMock()
        browser_pool.browsers = [mock_browser1, mock_browser2]
        
        mock_playwright = AsyncMock()
        browser_pool._playwright = mock_playwright
        
        await browser_pool.close()
        
        mock_browser1.close.assert_called_once()
        mock_browser2.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_browser_pool_no_playwright(self, browser_pool):
        """Test closing browser pool without playwright instance."""
        mock_browser = AsyncMock()
        browser_pool.browsers = [mock_browser]
        browser_pool._playwright = None
        
        await browser_pool.close()
        
        mock_browser.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_browser_context_manager(self, browser_pool):
        """Test browser context manager."""
        mock_browser = AsyncMock()
        browser_pool.browsers = [mock_browser]
        
        async with browser_pool.get_browser() as browser:
            assert browser == mock_browser
            assert len(browser_pool.browsers) == 0
        
        # Browser should be returned to pool
        assert len(browser_pool.browsers) == 1
        assert browser_pool.browsers[0] == mock_browser
    
    @pytest.mark.asyncio
    async def test_get_browser_empty_pool(self, browser_pool):
        """Test getting browser from empty pool."""
        browser_pool.browsers = []
        
        with pytest.raises(PNGGenerationError, match="Browser pool not initialized"):
            async with browser_pool.get_browser():
                pass
    
    @pytest.mark.asyncio
    async def test_get_browser_exception_handling(self, browser_pool):
        """Test browser context manager exception handling."""
        mock_browser = AsyncMock()
        browser_pool.browsers = [mock_browser]
        
        try:
            async with browser_pool.get_browser() as browser:
                assert browser == mock_browser
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Browser should still be returned to pool
        assert len(browser_pool.browsers) == 1
        assert browser_pool.browsers[0] == mock_browser


class TestPlaywrightPNGGenerator:
    """Test Playwright PNG generator."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.browser_pool_size = 2
        settings.playwright_timeout = 30000
        settings.playwright_headless = True
        return settings
    
    @pytest.fixture
    def mock_browser_pool(self):
        """Create mock browser pool."""
        pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        pool.get_browser = mock_get_browser
        return pool
    
    @pytest.fixture
    def generator_with_pool(self, mock_browser_pool, mock_settings):
        """Create PNG generator with mock browser pool."""
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            return PlaywrightPNGGenerator(mock_browser_pool)
    
    @pytest.fixture
    def generator_own_pool(self, mock_settings):
        """Create PNG generator with own browser pool."""
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            return PlaywrightPNGGenerator()
    
    @pytest.fixture
    def sample_options(self):
        """Create sample render options."""
        return RenderOptionsGenerator.generate_basic_options()
    
    def test_generator_initialization_with_pool(self, generator_with_pool, mock_browser_pool):
        """Test generator initialization with provided pool."""
        assert generator_with_pool.browser_pool == mock_browser_pool
        assert generator_with_pool._own_pool is False
        assert generator_with_pool.settings is not None
        assert generator_with_pool.logger is not None
    
    def test_generator_initialization_own_pool(self, generator_own_pool):
        """Test generator initialization with own pool."""
        assert generator_own_pool.browser_pool is not None
        assert generator_own_pool._own_pool is True
    
    @pytest.mark.asyncio
    async def test_initialize_with_own_pool(self, generator_own_pool):
        """Test initializing generator with own pool."""
        with patch.object(generator_own_pool.browser_pool, 'initialize') as mock_init:
            await generator_own_pool.initialize()
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_without_own_pool(self, generator_with_pool):
        """Test initializing generator without own pool."""
        with patch.object(generator_with_pool.browser_pool, 'initialize') as mock_init:
            await generator_with_pool.initialize()
            mock_init.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_close_with_own_pool(self, generator_own_pool):
        """Test closing generator with own pool."""
        with patch.object(generator_own_pool.browser_pool, 'close') as mock_close:
            await generator_own_pool.close()
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_without_own_pool(self, generator_with_pool):
        """Test closing generator without own pool."""
        with patch.object(generator_with_pool.browser_pool, 'close') as mock_close:
            await generator_with_pool.close()
            mock_close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_png_success(self, generator_with_pool, sample_options):
        """Test successful PNG generation."""
        html_content = "<html><body>Test</body></html>"
        
        # Mock browser components
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'mock_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        
        @asynccontextmanager
        async def mock_get_browser():
            yield mock_browser
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', return_value=mock_context):
            with patch.object(generator_with_pool, '_configure_page') as mock_configure:
                result = await generator_with_pool.generate_png(html_content, sample_options)
                
                assert_valid_png_result(result)
                assert result.png_data == b'mock_png_data'
                assert result.base64_data == base64.b64encode(b'mock_png_data').decode('utf-8')
                assert result.file_size == len(b'mock_png_data')
                assert result.metadata['generator'] == 'playwright'
                
                mock_configure.assert_called_once()
                mock_page.set_content.assert_called_once_with(html_content, wait_until="domcontentloaded")
                mock_context.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_png_with_optimization(self, generator_with_pool, sample_options):
        """Test PNG generation with optimization."""
        html_content = "<html><body>Test</body></html>"
        sample_options.optimize_png = True
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'original_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        
        @asynccontextmanager
        async def mock_get_browser():
            yield mock_browser
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', return_value=mock_context):
            with patch.object(generator_with_pool, '_configure_page'):
                with patch.object(generator_with_pool, '_optimize_png', return_value=b'optimized_png_data') as mock_optimize:
                    result = await generator_with_pool.generate_png(html_content, sample_options)
                    
                    assert result.png_data == b'optimized_png_data'
                    mock_optimize.assert_called_once_with(b'original_png_data', sample_options)
    
    @pytest.mark.asyncio
    async def test_generate_png_with_wait_for_load(self, generator_with_pool, sample_options):
        """Test PNG generation with wait for load."""
        html_content = "<html><body>Test</body></html>"
        sample_options.wait_for_load = True
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'mock_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', return_value=mock_context):
            with patch.object(generator_with_pool, '_configure_page'):
                await generator_with_pool.generate_png(html_content, sample_options)
                
                mock_page.wait_for_load_state.assert_called_once_with("networkidle")
    
    @pytest.mark.asyncio
    async def test_generate_png_full_page(self, generator_with_pool, sample_options):
        """Test PNG generation with full page screenshot."""
        html_content = "<html><body>Test</body></html>"
        sample_options.full_page = True
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'mock_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', return_value=mock_context):
            with patch.object(generator_with_pool, '_configure_page'):
                await generator_with_pool.generate_png(html_content, sample_options)
                
                # Verify screenshot called with full_page=True and no clip
                mock_page.screenshot.assert_called_once_with(
                    type="png",
                    full_page=True,
                    clip=None
                )
    
    @pytest.mark.asyncio
    async def test_generate_png_clipped(self, generator_with_pool, sample_options):
        """Test PNG generation with clipped screenshot."""
        html_content = "<html><body>Test</body></html>"
        sample_options.full_page = False
        sample_options.width = 800
        sample_options.height = 600
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'mock_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', return_value=mock_context):
            with patch.object(generator_with_pool, '_configure_page'):
                await generator_with_pool.generate_png(html_content, sample_options)
                
                # Verify screenshot called with clip parameters
                mock_page.screenshot.assert_called_once_with(
                    type="png",
                    full_page=False,
                    clip={"x": 0, "y": 0, "width": 800, "height": 600}
                )
    
    @pytest.mark.asyncio
    async def test_generate_png_error_handling(self, generator_with_pool, sample_options):
        """Test PNG generation error handling."""
        html_content = "<html><body>Test</body></html>"
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        generator_with_pool.browser_pool.get_browser = mock_get_browser
        
        with patch.object(generator_with_pool, '_create_browser_context', side_effect=Exception("Context error")):
            with pytest.raises(PNGGenerationError, match="PNG generation failed"):
                await generator_with_pool.generate_png(html_content, sample_options)
    
    @pytest.mark.asyncio
    async def test_create_browser_context(self, generator_with_pool, sample_options):
        """Test browser context creation."""
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = AsyncMock()
        
        context = await generator_with_pool._create_browser_context(mock_browser, sample_options)
        
        mock_browser.new_context.assert_called_once()
        call_args = mock_browser.new_context.call_args[1]
        
        assert call_args['viewport']['width'] == sample_options.width
        assert call_args['viewport']['height'] == sample_options.height
        assert call_args['device_scale_factor'] == sample_options.device_scale_factor
    
    @pytest.mark.asyncio
    async def test_create_browser_context_with_user_agent(self, generator_with_pool, sample_options):
        """Test browser context creation with custom user agent."""
        sample_options.user_agent = "Custom User Agent"
        
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = AsyncMock()
        
        await generator_with_pool._create_browser_context(mock_browser, sample_options)
        
        call_args = mock_browser.new_context.call_args[1]
        assert call_args['user_agent'] == "Custom User Agent"
    
    @pytest.mark.asyncio
    async def test_configure_page_basic(self, generator_with_pool, sample_options):
        """Test basic page configuration."""
        mock_page = AsyncMock()
        
        await generator_with_pool._configure_page(mock_page, sample_options)
        
        mock_page.set_default_timeout.assert_called_once_with(
            generator_with_pool.settings.playwright_timeout
        )
    
    @pytest.mark.asyncio
    async def test_configure_page_with_resource_blocking(self, generator_with_pool, sample_options):
        """Test page configuration with resource blocking."""
        sample_options.block_resources = True
        
        mock_page = AsyncMock()
        
        await generator_with_pool._configure_page(mock_page, sample_options)
        
        mock_page.route.assert_called_once_with("**/*", generator_with_pool._handle_route)
    
    @pytest.mark.asyncio
    async def test_handle_route_block_image(self, generator_with_pool):
        """Test route handling for blocked resources."""
        mock_route = AsyncMock()
        mock_route.request.resource_type = "image"
        
        await generator_with_pool._handle_route(mock_route)
        
        mock_route.abort.assert_called_once()
        mock_route.continue_.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_route_allow_document(self, generator_with_pool):
        """Test route handling for allowed resources."""
        mock_route = AsyncMock()
        mock_route.request.resource_type = "document"
        
        await generator_with_pool._handle_route(mock_route)
        
        mock_route.continue_.assert_called_once()
        mock_route.abort.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_optimize_png_transparent_background(self, generator_with_pool, sample_options):
        """Test PNG optimization with transparent background."""
        sample_options.transparent_background = True
        sample_options.optimize_png = True
        
        # Create mock PIL Image
        mock_image = Mock()
        mock_image.mode = 'RGB'
        mock_image.convert.return_value = mock_image
        mock_image.getdata.return_value = [(255, 255, 255), (100, 100, 100)]
        
        mock_output = Mock()
        mock_output.getvalue.return_value = b'optimized_data'
        
        with patch('src.core.rendering.png_generator.Image') as mock_pil:
            with patch('src.core.rendering.png_generator.io.BytesIO', return_value=mock_output):
                mock_pil.open.return_value = mock_image
                
                result = await generator_with_pool._optimize_png(b'original_data', sample_options)
                
                assert result == b'optimized_data'
                mock_image.convert.assert_called_with('RGBA')
                mock_image.putdata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_png_quality_reduction(self, generator_with_pool, sample_options):
        """Test PNG optimization with quality reduction."""
        sample_options.png_quality = 80
        sample_options.optimize_png = True
        
        mock_image = Mock()
        mock_image.mode = 'RGB'
        mock_image.quantize.return_value = mock_image
        
        mock_output = Mock()
        mock_output.getvalue.return_value = b'optimized_data'
        
        with patch('src.core.rendering.png_generator.Image') as mock_pil:
            with patch('src.core.rendering.png_generator.io.BytesIO', return_value=mock_output):
                mock_pil.open.return_value = mock_image
                
                result = await generator_with_pool._optimize_png(b'original_data', sample_options)
                
                assert result == b'optimized_data'
                mock_image.quantize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_png_error_handling(self, generator_with_pool, sample_options):
        """Test PNG optimization error handling."""
        with patch('src.core.rendering.png_generator.Image') as mock_pil:
            mock_pil.open.side_effect = Exception("PIL error")
            
            result = await generator_with_pool._optimize_png(b'original_data', sample_options)
            
            # Should return original data on error
            assert result == b'original_data'


class TestAdvancedPNGGenerator:
    """Test advanced PNG generator."""
    
    @pytest.fixture
    def mock_browser_pool(self):
        """Create mock browser pool."""
        pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        pool.get_browser = mock_get_browser
        return pool
    
    @pytest.fixture
    def advanced_generator(self, mock_browser_pool):
        """Create advanced PNG generator."""
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = AdvancedPNGGenerator(mock_browser_pool)
            return generator
    
    @pytest.fixture
    def sample_options(self):
        """Create sample render options."""
        return RenderOptionsGenerator.generate_basic_options()
    
    def test_advanced_generator_initialization(self, advanced_generator):
        """Test advanced generator initialization."""
        assert advanced_generator.performance_metrics == {}
        assert advanced_generator.device_presets is not None
        assert 'desktop' in advanced_generator.device_presets
        assert 'tablet' in advanced_generator.device_presets
        assert 'mobile' in advanced_generator.device_presets
    
    def test_device_presets_setup(self, advanced_generator):
        """Test device presets configuration."""
        presets = advanced_generator.device_presets
        
        # Check desktop preset
        assert presets['desktop']['viewport']['width'] == 1920
        assert presets['desktop']['viewport']['height'] == 1080
        assert presets['desktop']['device_scale_factor'] == 1.0
        
        # Check tablet preset
        assert presets['tablet']['viewport']['width'] == 768
        assert presets['tablet']['viewport']['height'] == 1024
        assert presets['tablet']['device_scale_factor'] == 2.0
        
        # Check mobile preset
        assert presets['mobile']['viewport']['width'] == 375
        assert presets['mobile']['viewport']['height'] == 667
        assert presets['mobile']['device_scale_factor'] == 3.0
    
    @pytest.mark.asyncio
    async def test_generate_png_with_device_emulation_desktop(self, advanced_generator, sample_options):
        """Test PNG generation with desktop device emulation."""
        html_content = "<html><body>Test</body></html>"
        
        with patch.object(advanced_generator, 'generate_png') as mock_generate:
            mock_result = Mock(spec=PNGResult)
            mock_result.metadata = {}
            mock_generate.return_value = mock_result
            
            result = await advanced_generator.generate_png_with_device_emulation(
                html_content, sample_options, "desktop"
            )
            
            assert result.metadata['device_type'] == 'desktop'
            assert 'device_config' in result.metadata
            
            # Verify enhanced options were used
            call_args = mock_generate.call_args[0]
            enhanced_options = call_args[1]
            assert enhanced_options.width == 1920
            assert enhanced_options.height == 1080
            assert enhanced_options.device_scale_factor == 1.0
    
    @pytest.mark.asyncio
    async def test_generate_png_with_device_emulation_invalid_device(self, advanced_generator, sample_options):
        """Test PNG generation with invalid device type."""
        html_content = "<html><body>Test</body></html>"
        
        with patch.object(advanced_generator, 'generate_png') as mock_generate:
            mock_result = Mock(spec=PNGResult)
            mock_result.metadata = {}
            mock_generate.return_value = mock_result
            
            result = await advanced_generator.generate_png_with_device_emulation(
                html_content, sample_options, "invalid_device"
            )
            
            # Should default to desktop
            assert result.metadata['device_type'] == 'desktop'
    
    @pytest.mark.asyncio
    async def test_generate_responsive_screenshots(self, advanced_generator, sample_options):
        """Test generating responsive screenshots for all devices."""
        html_content = "<html><body>Test</body></html>"
        
        with patch.object(advanced_generator, 'generate_png_with_device_emulation') as mock_generate:
            mock_result = Mock(spec=PNGResult)
            mock_result.file_size = 1024
            mock_generate.return_value = mock_result
            
            results = await advanced_generator.generate_responsive_screenshots(
                html_content, sample_options
            )
            
            assert len(results) == 3
            assert 'desktop' in results
            assert 'tablet' in results
            assert 'mobile' in results
            
            assert mock_generate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_responsive_screenshots_with_error(self, advanced_generator, sample_options):
        """Test responsive screenshots with partial failures."""
        html_content = "<html><body>Test</body></html>"
        
        def mock_generate_side_effect(content, options, device_type):
            if device_type == 'tablet':
                raise Exception("Tablet generation failed")
            mock_result = Mock(spec=PNGResult)
            mock_result.file_size = 1024
            return mock_result
        
        with patch.object(advanced_generator, 'generate_png_with_device_emulation', side_effect=mock_generate_side_effect):
            results = await advanced_generator.generate_responsive_screenshots(
                html_content, sample_options
            )
            
            # Should have results for desktop and mobile, but not tablet
            assert len(results) == 2
            assert 'desktop' in results
            assert 'mobile' in results
            assert 'tablet' not in results
    
    @pytest.mark.asyncio
    async def test_capture_element_screenshot_success(self, advanced_generator, sample_options):
        """Test capturing element screenshot successfully."""
        html_content = "<html><body><div id='target'>Content</div></body></html>"
        element_selector = "#target"
        
        # Mock element and page
        mock_element = AsyncMock()
        mock_element.screenshot.return_value = b'element_screenshot_data'
        mock_element.bounding_box.return_value = {'width': 200, 'height': 100}
        
        mock_page = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        advanced_generator.browser_pool.get_browser = mock_get_browser
        
        with patch.object(advanced_generator, '_create_browser_context', return_value=mock_context):
            with patch.object(advanced_generator, '_configure_page'):
                result = await advanced_generator.capture_element_screenshot(
                    html_content, sample_options, element_selector
                )
                
                assert result is not None
                assert result.png_data == b'element_screenshot_data'
                assert result.width == 200
                assert result.height == 100
                assert result.metadata['generator'] == 'playwright_element'
                assert result.metadata['element_selector'] == element_selector
                
                mock_page.wait_for_selector.assert_called_once_with(element_selector, timeout=5000)
                mock_element.screenshot.assert_called_once_with(type="png")
    
    @pytest.mark.asyncio
    async def test_capture_element_screenshot_element_not_found(self, advanced_generator, sample_options):
        """Test capturing element screenshot when element not found."""
        html_content = "<html><body>No target</body></html>"
        element_selector = "#nonexistent"
        
        mock_page = AsyncMock()
        mock_page.wait_for_selector.return_value = None
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        advanced_generator.browser_pool.get_browser = mock_get_browser
        
        with patch.object(advanced_generator, '_create_browser_context', return_value=mock_context):
            with patch.object(advanced_generator, '_configure_page'):
                result = await advanced_generator.capture_element_screenshot(
                    html_content, sample_options, element_selector
                )
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_capture_element_screenshot_error(self, advanced_generator, sample_options):
        """Test element screenshot error handling."""
        html_content = "<html><body>Test</body></html>"
        element_selector = "#target"
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        advanced_generator.browser_pool.get_browser = mock_get_browser
        
        with patch.object(advanced_generator, '_create_browser_context', side_effect=Exception("Context error")):
            result = await advanced_generator.capture_element_screenshot(
                html_content, sample_options, element_selector
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, advanced_generator):
        """Test getting performance metrics."""
        # Mock browser pool browsers
        advanced_generator.browser_pool.browsers = [Mock(), Mock()]
        
        with patch.object(advanced_generator, '_get_memory_usage', return_value={'memory_mb': 100.5, 'memory_percent': 5.2}):
            metrics = await advanced_generator.get_performance_metrics()
            
            assert metrics['browser_pool_size'] == 2
            assert 'active_contexts' in metrics
            assert 'total_screenshots' in metrics
            assert 'average_generation_time' in metrics
            assert 'memory_usage' in metrics
            assert metrics['memory_usage']['memory_mb'] == 100.5
    
    def test_get_memory_usage(self, advanced_generator):
        """Test memory usage calculation."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 104857600  # 100 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 5.5
        
        with patch('psutil.Process', return_value=mock_process):
            memory_usage = advanced_generator._get_memory_usage()
            
            assert memory_usage['memory_mb'] == 100.0  # 104857600 / 1024 / 1024
            assert memory_usage['memory_percent'] == 5.5


class TestPNGGeneratorFactory:
    """Test PNG generator factory."""
    
    @pytest.fixture
    def mock_browser_pool(self):
        """Create mock browser pool."""
        return Mock(spec=BrowserPool)
    
    def test_create_playwright_generator(self, mock_browser_pool):
        """Test creating Playwright generator."""
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PNGGeneratorFactory.create_generator("playwright", mock_browser_pool)
            assert isinstance(generator, PlaywrightPNGGenerator)
            assert generator.browser_pool == mock_browser_pool
    
    def test_create_advanced_generator(self, mock_browser_pool):
        """Test creating advanced generator."""
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PNGGeneratorFactory.create_generator("advanced", mock_browser_pool)
            assert isinstance(generator, AdvancedPNGGenerator)
            assert generator.browser_pool == mock_browser_pool
    
    def test_create_invalid_generator_type(self, mock_browser_pool):
        """Test creating generator with invalid type."""
        with patch('src.core.rendering.png_generator.get_settings'):
            # Should default to playwright
            generator = PNGGeneratorFactory.create_generator("invalid", mock_browser_pool)
            assert isinstance(generator, PlaywrightPNGGenerator)
    
    def test_create_generator_default_type(self, mock_browser_pool):
        """Test creating generator with default type."""
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PNGGeneratorFactory.create_generator(browser_pool=mock_browser_pool)
            assert isinstance(generator, PlaywrightPNGGenerator)
    
    def test_create_generator_without_pool(self):
        """Test creating generator without browser pool."""
        mock_settings = Mock()
        mock_settings.browser_pool_size = 2
        mock_settings.playwright_timeout = 30000
        mock_settings.playwright_headless = True
        
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            generator = PNGGeneratorFactory.create_generator("playwright")
            assert isinstance(generator, PlaywrightPNGGenerator)
            assert generator.browser_pool is not None


class TestGlobalBrowserPoolFunctions:
    """Test global browser pool management functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.browser_pool_size = 3
        return settings
    
    @pytest.mark.asyncio
    async def test_initialize_browser_pool(self, mock_settings):
        """Test initializing global browser pool."""
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            with patch('src.core.rendering.png_generator.BrowserPool') as mock_pool_class:
                mock_pool = AsyncMock()
                mock_pool_class.return_value = mock_pool
                
                await initialize_browser_pool()
                
                mock_pool_class.assert_called_once_with(3)
                mock_pool.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_browser_pool_existing(self):
        """Test closing existing global browser pool."""
        mock_pool = AsyncMock()
        
        with patch('src.core.rendering.png_generator._global_browser_pool', mock_pool):
            await close_browser_pool()
            mock_pool.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_browser_pool_none(self):
        """Test closing when no global browser pool exists."""
        with patch('src.core.rendering.png_generator._global_browser_pool', None):
            # Should not raise error
            await close_browser_pool()
    
    @pytest.mark.asyncio
    async def test_generate_png_from_html_success(self):
        """Test generating PNG from HTML using global pool."""
        html_content = "<html><body>Test</body></html>"
        options = Mock(spec=RenderOptions)
        
        mock_pool = Mock(spec=BrowserPool)
        mock_result = Mock(spec=PNGResult)
        
        with patch('src.core.rendering.png_generator._global_browser_pool', mock_pool):
            with patch('src.core.rendering.png_generator.PlaywrightPNGGenerator') as mock_generator_class:
                mock_generator = AsyncMock()
                mock_generator.generate_png.return_value = mock_result
                mock_generator_class.return_value = mock_generator
                
                result = await generate_png_from_html(html_content, options)
                
                assert result == mock_result
                mock_generator_class.assert_called_once_with(mock_pool)
                mock_generator.generate_png.assert_called_once_with(html_content, options)
    
    @pytest.mark.asyncio
    async def test_generate_png_from_html_no_pool(self):
        """Test generating PNG when no global pool exists."""
        html_content = "<html><body>Test</body></html>"
        options = Mock(spec=RenderOptions)
        
        with patch('src.core.rendering.png_generator._global_browser_pool', None):
            with pytest.raises(PNGGenerationError, match="Browser pool not initialized"):
                await generate_png_from_html(html_content, options)


class TestPNGGeneratorPerformance:
    """Test PNG generator performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_png_generation_performance(self):
        """Test PNG generation performance."""
        html_content = "<html><body>" + "Test content " * 100 + "</body></html>"
        options = RenderOptionsGenerator.generate_basic_options()
        
        # Mock all dependencies for performance test
        mock_pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        mock_pool.get_browser = mock_get_browser
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'mock_png_data' * 1000  # Larger mock data
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PlaywrightPNGGenerator(mock_pool)
            
            with patch.object(generator, '_create_browser_context', return_value=mock_context):
                with patch.object(generator, '_configure_page'):
                    with TestTimer("PNG generation") as timer:
                        result = await generator.generate_png(html_content, options)
                    
                    assert result.png_data is not None
                    # Performance should be reasonable for mocked operations
                    assert timer.duration < 0.1
    
    @pytest.mark.asyncio
    async def test_browser_pool_concurrent_access(self):
        """Test browser pool performance with concurrent access."""
        mock_settings = Mock()
        mock_settings.browser_pool_size = 2
        mock_settings.playwright_timeout = 30000
        mock_settings.playwright_headless = True
        
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            pool = BrowserPool(pool_size=2)
            
            # Mock browsers
            mock_browser1 = AsyncMock()
            mock_browser2 = AsyncMock()
            pool.browsers = [mock_browser1, mock_browser2]
            
            async def get_browser_task():
                async with pool.get_browser() as browser:
                    await asyncio.sleep(0.01)  # Simulate work
                    return browser
            
            # Run concurrent tasks
            tasks = [get_browser_task() for _ in range(10)]
            
            with TestTimer("Concurrent browser pool access") as timer:
                results = await asyncio.gather(*tasks)
            
            assert len(results) == 10
            assert timer.duration < 0.5  # Should complete quickly with mocks


class TestPNGGeneratorEdgeCases:
    """Test PNG generator edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_generate_png_with_large_html_content(self):
        """Test PNG generation with very large HTML content."""
        # Create large HTML content
        large_content = "<html><body>" + "Large content " * 10000 + "</body></html>"
        options = RenderOptionsGenerator.generate_basic_options()
        
        mock_pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        mock_pool.get_browser = mock_get_browser
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'large_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PlaywrightPNGGenerator(mock_pool)
            
            with patch.object(generator, '_create_browser_context', return_value=mock_context):
                with patch.object(generator, '_configure_page'):
                    result = await generator.generate_png(large_content, options)
                    
                    assert result.png_data == b'large_png_data'
                    assert len(large_content) > 100000  # Verify content is actually large
    
    @pytest.mark.asyncio
    async def test_generate_png_with_unicode_content(self):
        """Test PNG generation with unicode HTML content."""
        unicode_html = "<html><body><h1>测试标题 🌍</h1><p>Тест контент</p></body></html>"
        options = RenderOptionsGenerator.generate_basic_options()
        
        mock_pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        mock_pool.get_browser = mock_get_browser
        
        mock_page = AsyncMock()
        mock_page.screenshot.return_value = b'unicode_png_data'
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = PlaywrightPNGGenerator(mock_pool)
            
            with patch.object(generator, '_create_browser_context', return_value=mock_context):
                with patch.object(generator, '_configure_page'):
                    result = await generator.generate_png(unicode_html, options)
                    
                    assert result.png_data == b'unicode_png_data'
                    mock_page.set_content.assert_called_once_with(unicode_html, wait_until="domcontentloaded")
    
    @pytest.mark.asyncio
    async def test_png_optimization_rgba_mode(self):
        """Test PNG optimization with RGBA mode image."""
        options = RenderOptionsGenerator.generate_basic_options()
        options.optimize_png = True
        options.transparent_background = False
        
        mock_image = Mock()
        mock_image.mode = 'RGBA'
        mock_image.save = Mock()
        
        mock_output = Mock()
        mock_output.getvalue.return_value = b'rgba_optimized_data'
        
        mock_settings = Mock()
        mock_settings.browser_pool_size = 2
        mock_settings.playwright_timeout = 30000
        mock_settings.playwright_headless = True
        
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            generator = PlaywrightPNGGenerator()
            
            with patch('src.core.rendering.png_generator.Image') as mock_pil:
                with patch('src.core.rendering.png_generator.io.BytesIO', return_value=mock_output):
                    mock_pil.open.return_value = mock_image
                    
                    result = await generator._optimize_png(b'original_rgba_data', options)
                    
                    assert result == b'rgba_optimized_data'
                    # Verify save was called with transparency support
                    save_kwargs = mock_image.save.call_args[1]
                    assert save_kwargs['transparency'] == 0
    
    @pytest.mark.asyncio
    async def test_browser_pool_initialization_partial_failure(self):
        """Test browser pool initialization with partial browser failures."""
        mock_settings = Mock()
        mock_settings.playwright_headless = True
        
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            pool = BrowserPool(pool_size=3)
            
            # Mock playwright with partial failure
            mock_browser1 = AsyncMock()
            mock_browser2 = AsyncMock()
            
            mock_chromium = AsyncMock()
            # First two succeed, third fails
            mock_chromium.launch.side_effect = [mock_browser1, mock_browser2, Exception("Browser 3 failed")]
            
            mock_playwright = AsyncMock()
            mock_playwright.chromium = mock_chromium
            
            with patch('src.core.rendering.png_generator.async_playwright') as mock_async_playwright:
                mock_async_playwright.return_value.start.return_value = mock_playwright
                
                with pytest.raises(PNGGenerationError, match="Browser pool initialization failed"):
                    await pool.initialize()
    
    def test_device_presets_user_agents(self):
        """Test device presets contain proper user agents."""
        mock_settings = Mock()
        mock_settings.browser_pool_size = 2
        mock_settings.playwright_timeout = 30000
        mock_settings.playwright_headless = True
        
        with patch('src.core.rendering.png_generator.get_settings', return_value=mock_settings):
            generator = AdvancedPNGGenerator()
            
            presets = generator.device_presets
            
            # Verify user agents are device-specific
            assert 'Windows' in presets['desktop']['user_agent']
            assert 'iPad' in presets['tablet']['user_agent']
            assert 'iPhone' in presets['mobile']['user_agent']
    
    @pytest.mark.asyncio
    async def test_element_screenshot_with_no_bounding_box(self):
        """Test element screenshot when element has no bounding box."""
        options = RenderOptionsGenerator.generate_basic_options()
        html_content = "<html><body><div id='target'>Content</div></body></html>"
        
        mock_element = AsyncMock()
        mock_element.screenshot.return_value = b'element_data'
        mock_element.bounding_box.return_value = None  # No bounding box
        
        mock_page = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_pool = AsyncMock(spec=BrowserPool)
        
        @asynccontextmanager
        async def mock_get_browser():
            yield AsyncMock()
        
        mock_pool.get_browser = mock_get_browser
        
        with patch('src.core.rendering.png_generator.get_settings'):
            generator = AdvancedPNGGenerator(mock_pool)
            
            with patch.object(generator, '_create_browser_context', return_value=mock_context):
                with patch.object(generator, '_configure_page'):
                    result = await generator.capture_element_screenshot(
                        html_content, options, "#target"
                    )
                    
                    assert result is not None
                    # Should use options dimensions when no bounding box
                    assert result.width == options.width
                    assert result.height == options.height