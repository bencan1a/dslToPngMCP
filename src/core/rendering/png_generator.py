"""
PNG Generator
=============

Playwright-based PNG screenshot generation from HTML content.
Manages browser instances, viewport configuration, and image optimization.
"""

from typing import Optional, Dict, Any, List
import asyncio
from pathlib import Path
import base64
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from PIL import Image
import io

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.models.schemas import RenderOptions, PNGResult

logger = get_logger(__name__)


class PNGGenerationError(Exception):
    """Exception raised when PNG generation fails."""
    pass


class BrowserPool:
    """Browser instance pool for efficient resource management."""
    
    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self.browsers: List[Browser] = []
        self._semaphore = asyncio.Semaphore(pool_size)
        self._playwright = None
        self.settings = get_settings()
        self.logger = logger.bind(component="browser_pool")
    
    async def initialize(self) -> None:
        """Initialize browser pool."""
        try:
            self._playwright = await async_playwright().start()
            
            for i in range(self.pool_size):
                browser = await self._playwright.chromium.launch(
                    headless=self.settings.playwright_headless,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                self.browsers.append(browser)
            
            self.logger.info("Browser pool initialized", pool_size=self.pool_size)
        except Exception as e:
            self.logger.error("Failed to initialize browser pool", error=str(e))
            raise PNGGenerationError(f"Browser pool initialization failed: {e}")
    
    async def close(self) -> None:
        """Close all browsers in the pool."""
        for browser in self.browsers:
            await browser.close()
        
        if self._playwright:
            await self._playwright.stop()
        
        self.logger.info("Browser pool closed")
    
    @asynccontextmanager
    async def get_browser(self):
        """Get a browser instance from the pool."""
        async with self._semaphore:
            if not self.browsers:
                raise PNGGenerationError("Browser pool not initialized")
            
            browser = self.browsers.pop()
            try:
                yield browser
            finally:
                self.browsers.append(browser)


class PlaywrightPNGGenerator:
    """Playwright-based PNG generator implementation."""
    
    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self.settings = get_settings()
        self.logger = logger.bind(generator="playwright")
        self.browser_pool = browser_pool
        self._own_pool = browser_pool is None
        
        if self._own_pool:
            self.browser_pool = BrowserPool(self.settings.browser_pool_size)
    
    async def initialize(self) -> None:
        """Initialize the PNG generator."""
        if self._own_pool:
            await self.browser_pool.initialize()
        self.logger.info("PNG generator initialized")
    
    async def close(self) -> None:
        """Close the PNG generator."""
        if self._own_pool:
            await self.browser_pool.close()
        self.logger.info("PNG generator closed")
    
    async def generate_png(self, html_content: str, options: RenderOptions) -> PNGResult:
        """
        Generate PNG from HTML content.
        
        Args:
            html_content: HTML content to render
            options: Rendering options
            
        Returns:
            PNGResult containing PNG data and metadata
            
        Raises:
            PNGGenerationError: If PNG generation fails
        """
        try:
            self.logger.info("Generating PNG from HTML", 
                           html_length=len(html_content),
                           width=options.width,
                           height=options.height)
            
            async with self.browser_pool.get_browser() as browser:
                context = await self._create_browser_context(browser, options)
                
                try:
                    page = await context.new_page()
                    
                    # Configure page
                    await self._configure_page(page, options)
                    
                    # Set HTML content
                    await page.set_content(html_content, wait_until="domcontentloaded")
                    
                    # Wait for any additional loading
                    if options.wait_for_load:
                        await page.wait_for_load_state("networkidle")
                    
                    # Take screenshot
                    screenshot_bytes = await page.screenshot(
                        type="png",
                        full_page=options.full_page,
                        clip={
                            "x": 0,
                            "y": 0,
                            "width": options.width,
                            "height": options.height
                        } if not options.full_page else None
                    )
                    
                    # Process image if needed
                    if options.optimize_png:
                        screenshot_bytes = await self._optimize_png(screenshot_bytes, options)
                    
                    # Prepare result
                    result = PNGResult(
                        png_data=screenshot_bytes,
                        base64_data=base64.b64encode(screenshot_bytes).decode('utf-8'),
                        width=options.width,
                        height=options.height,
                        file_size=len(screenshot_bytes),
                        metadata={
                            "generator": "playwright",
                            "optimization": options.optimize_png,
                            "full_page": options.full_page
                        }
                    )
                    
                    self.logger.info("PNG generation completed",
                                   file_size=result.file_size,
                                   optimized=options.optimize_png)
                    
                    return result
                    
                finally:
                    await context.close()
        
        except Exception as e:
            error_msg = f"PNG generation failed: {e}"
            self.logger.error("PNG generation error", error=error_msg)
            raise PNGGenerationError(error_msg)
    
    async def _create_browser_context(self, browser: Browser, options: RenderOptions) -> BrowserContext:
        """Create browser context with appropriate settings."""
        context_options = {
            "viewport": {
                "width": options.width,
                "height": options.height
            },
            "device_scale_factor": options.device_scale_factor,
            "user_agent": options.user_agent if options.user_agent else None,
        }
        
        return await browser.new_context(**context_options)
    
    async def _configure_page(self, page: Page, options: RenderOptions) -> None:
        """Configure page settings."""
        # Set timeout
        page.set_default_timeout(self.settings.playwright_timeout)
        
        # Block unnecessary resources if requested
        if options.block_resources:
            await page.route("**/*", self._handle_route)
    
    async def _handle_route(self, route) -> None:
        """Handle resource blocking."""
        resource_type = route.request.resource_type
        
        # Block images, fonts, and other non-essential resources for faster rendering
        if resource_type in ["image", "font", "media", "other"]:
            await route.abort()
        else:
            await route.continue_()
    
    async def _optimize_png(self, png_bytes: bytes, options: RenderOptions) -> bytes:
        """
        Optimize PNG image using PIL.
        
        Args:
            png_bytes: Original PNG bytes
            options: Rendering options
            
        Returns:
            Optimized PNG bytes
        """
        try:
            # Load image with PIL
            image = Image.open(io.BytesIO(png_bytes))
            
            # Apply transparency background if requested
            if options.transparent_background:
                # Convert to RGBA if not already
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                # Make white pixels transparent
                data = image.getdata()
                new_data = []
                for item in data:
                    # Replace white (or near-white) with transparent
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        new_data.append((255, 255, 255, 0))  # Transparent
                    else:
                        new_data.append(item)
                image.putdata(new_data)
            
            # Apply quality reduction if specified
            if options.png_quality and options.png_quality < 100:
                # Reduce color palette for smaller file size
                if image.mode == 'RGBA':
                    # Convert to palette mode with transparency
                    image = image.quantize(colors=256, method=Image.MEDIANCUT)
                elif image.mode == 'RGB':
                    # Convert to palette mode
                    image = image.quantize(colors=min(256, int(256 * options.png_quality / 100)))
            
            # Save optimized image
            output = io.BytesIO()
            save_kwargs = {
                'format': 'PNG',
                'optimize': True,
                'compress_level': 9 if options.optimize_png else 6
            }
            
            # Add transparency support
            if image.mode in ('RGBA', 'LA'):
                save_kwargs['transparency'] = 0
            
            image.save(output, **save_kwargs)
            optimized_bytes = output.getvalue()
            
            reduction = (1 - len(optimized_bytes) / len(png_bytes)) * 100 if len(png_bytes) > 0 else 0
            
            self.logger.debug("PNG optimization completed",
                            original_size=len(png_bytes),
                            optimized_size=len(optimized_bytes),
                            reduction_percent=round(reduction, 2))
            
            return optimized_bytes
            
        except Exception as e:
            self.logger.warning("PNG optimization failed, using original", error=str(e))
            return png_bytes


class AdvancedPNGGenerator(PlaywrightPNGGenerator):
    """Advanced PNG generator with device emulation and performance monitoring."""
    
    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        super().__init__(browser_pool)
        self.performance_metrics = {}
        self.device_presets = self._setup_device_presets()
    
    def _setup_device_presets(self) -> Dict[str, Dict[str, Any]]:
        """Setup device emulation presets."""
        return {
            'desktop': {
                'viewport': {'width': 1920, 'height': 1080},
                'device_scale_factor': 1.0,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'tablet': {
                'viewport': {'width': 768, 'height': 1024},
                'device_scale_factor': 2.0,
                'user_agent': 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            },
            'mobile': {
                'viewport': {'width': 375, 'height': 667},
                'device_scale_factor': 3.0,
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            }
        }
    
    async def generate_png_with_device_emulation(self, html_content: str,
                                               options: RenderOptions,
                                               device_type: str = 'desktop') -> PNGResult:
        """
        Generate PNG with device emulation.
        
        Args:
            html_content: HTML content to render
            options: Rendering options
            device_type: Device type ('desktop', 'tablet', 'mobile')
            
        Returns:
            PNGResult with device-specific rendering
        """
        if device_type not in self.device_presets:
            device_type = 'desktop'
        
        device_config = self.device_presets[device_type]
        
        # Override options with device config
        enhanced_options = RenderOptions(
            width=device_config['viewport']['width'],
            height=device_config['viewport']['height'],
            device_scale_factor=device_config['device_scale_factor'],
            user_agent=device_config['user_agent'],
            wait_for_load=options.wait_for_load,
            full_page=options.full_page,
            png_quality=options.png_quality,
            optimize_png=options.optimize_png,
            timeout=options.timeout,
            block_resources=options.block_resources,
            background_color=options.background_color,
            transparent_background=options.transparent_background
        )
        
        result = await self.generate_png(html_content, enhanced_options)
        result.metadata['device_type'] = device_type
        result.metadata['device_config'] = device_config
        
        return result
    
    async def generate_responsive_screenshots(self, html_content: str,
                                            base_options: RenderOptions) -> Dict[str, PNGResult]:
        """
        Generate screenshots for multiple device types.
        
        Args:
            html_content: HTML content to render
            base_options: Base rendering options
            
        Returns:
            Dictionary mapping device types to PNG results
        """
        results = {}
        
        for device_type in self.device_presets.keys():
            try:
                result = await self.generate_png_with_device_emulation(
                    html_content, base_options, device_type
                )
                results[device_type] = result
                
                self.logger.info("Generated responsive screenshot",
                               device_type=device_type,
                               file_size=result.file_size)
                
            except Exception as e:
                self.logger.error("Failed to generate responsive screenshot",
                                device_type=device_type, error=str(e))
        
        return results
    
    async def capture_element_screenshot(self, html_content: str, options: RenderOptions,
                                       element_selector: str) -> Optional[PNGResult]:
        """
        Capture screenshot of specific element.
        
        Args:
            html_content: HTML content to render
            options: Rendering options
            element_selector: CSS selector for target element
            
        Returns:
            PNGResult for the specific element or None if element not found
        """
        try:
            async with self.browser_pool.get_browser() as browser:
                context = await self._create_browser_context(browser, options)
                
                try:
                    page = await context.new_page()
                    await self._configure_page(page, options)
                    await page.set_content(html_content, wait_until="domcontentloaded")
                    
                    if options.wait_for_load:
                        await page.wait_for_load_state("networkidle")
                    
                    # Wait for element to be visible
                    element = await page.wait_for_selector(element_selector, timeout=5000)
                    
                    if not element:
                        self.logger.warning("Element not found", selector=element_selector)
                        return None
                    
                    # Take element screenshot
                    screenshot_bytes = await element.screenshot(type="png")
                    
                    if options.optimize_png:
                        screenshot_bytes = await self._optimize_png(screenshot_bytes, options)
                    
                    # Get element bounding box for dimensions
                    bounding_box = await element.bounding_box()
                    
                    result = PNGResult(
                        png_data=screenshot_bytes,
                        base64_data=base64.b64encode(screenshot_bytes).decode('utf-8'),
                        width=int(bounding_box['width']) if bounding_box else options.width,
                        height=int(bounding_box['height']) if bounding_box else options.height,
                        file_size=len(screenshot_bytes),
                        metadata={
                            'generator': 'playwright_element',
                            'element_selector': element_selector,
                            'bounding_box': bounding_box,
                            'optimization': options.optimize_png
                        }
                    )
                    
                    return result
                    
                finally:
                    await context.close()
                    
        except Exception as e:
            self.logger.error("Element screenshot failed",
                            selector=element_selector, error=str(e))
            return None
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            'browser_pool_size': len(self.browser_pool.browsers) if self.browser_pool else 0,
            'active_contexts': getattr(self, '_active_contexts', 0),
            'total_screenshots': getattr(self, '_total_screenshots', 0),
            'average_generation_time': getattr(self, '_avg_generation_time', 0.0),
            'memory_usage': self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        import psutil
        process = psutil.Process()
        return {
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'memory_percent': process.memory_percent()
        }


class PNGGeneratorFactory:
    """Factory for creating PNG generators."""
    
    _generators = {
        "playwright": PlaywrightPNGGenerator,
        "advanced": AdvancedPNGGenerator,
    }
    
    @classmethod
    def create_generator(cls, generator_type: str = "playwright",
                        browser_pool: Optional[BrowserPool] = None) -> PlaywrightPNGGenerator:
        """
        Create PNG generator instance.
        
        Args:
            generator_type: Type of generator
            browser_pool: Optional browser pool
            
        Returns:
            PNG generator instance
        """
        if generator_type not in cls._generators:
            generator_type = "playwright"
        
        return cls._generators[generator_type](browser_pool)


# Global browser pool instance
_global_browser_pool: Optional[BrowserPool] = None


async def initialize_browser_pool() -> None:
    """Initialize global browser pool."""
    global _global_browser_pool
    settings = get_settings()
    _global_browser_pool = BrowserPool(settings.browser_pool_size)
    await _global_browser_pool.initialize()


async def close_browser_pool() -> None:
    """Close global browser pool."""
    global _global_browser_pool
    if _global_browser_pool:
        await _global_browser_pool.close()
        _global_browser_pool = None


async def generate_png_from_html(html_content: str, options: RenderOptions) -> PNGResult:
    """
    Generate PNG from HTML using global browser pool.
    
    Args:
        html_content: HTML content to render
        options: Rendering options
        
    Returns:
        PNGResult containing PNG data and metadata
    """
    global _global_browser_pool
    
    # Auto-initialize browser pool if not already initialized
    if not _global_browser_pool:
        logger.info("Auto-initializing browser pool for PNG generation")
        await initialize_browser_pool()
    
    generator = PlaywrightPNGGenerator(_global_browser_pool)
    return await generator.generate_png(html_content, options)


async def run_browser_pool() -> None:
    """
    Run the browser pool service.
    
    This function initializes the global browser pool and keeps it running
    for use by other services. It handles graceful shutdown on interruption.
    """
    import signal
    import sys
    
    logger.info("Starting browser pool service...")
    
    # Initialize the browser pool
    await initialize_browser_pool()
    
    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, closing browser pool...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Browser pool service is ready")
        # Wait for shutdown signal
        await shutdown_event.wait()
    except Exception as e:
        logger.error("Browser pool service error", error=str(e))
    finally:
        logger.info("Shutting down browser pool service...")
        await close_browser_pool()
        logger.info("Browser pool service stopped")


# Alias for integration tests compatibility
PNGGenerator = PlaywrightPNGGenerator