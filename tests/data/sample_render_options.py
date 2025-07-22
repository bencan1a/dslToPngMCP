"""
Sample Render Options
====================

Collection of render option configurations for testing various rendering scenarios.
"""

from src.models.schemas import RenderOptions

# Basic Render Options
BASIC_RENDER_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

SMALL_RENDER_OPTIONS = RenderOptions(
    width=400,
    height=300,
    format="png",
    quality=85,
    device_scale_factor=1.0
)

LARGE_RENDER_OPTIONS = RenderOptions(
    width=1920,
    height=1080,
    format="png",
    quality=95,
    device_scale_factor=1.0
)

# High DPI Options
HIGH_DPI_RENDER_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=90,
    device_scale_factor=2.0
)

RETINA_RENDER_OPTIONS = RenderOptions(
    width=1024,
    height=768,
    format="png",
    quality=95,
    device_scale_factor=3.0
)

# Mobile Device Options
MOBILE_PORTRAIT_OPTIONS = RenderOptions(
    width=375,
    height=667,
    format="png",
    quality=85,
    device_scale_factor=2.0,
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
)

MOBILE_LANDSCAPE_OPTIONS = RenderOptions(
    width=667,
    height=375,
    format="png",
    quality=85,
    device_scale_factor=2.0,
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
)

TABLET_OPTIONS = RenderOptions(
    width=768,
    height=1024,
    format="png",
    quality=90,
    device_scale_factor=2.0,
    user_agent="Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
)

# Desktop Options
DESKTOP_SMALL_OPTIONS = RenderOptions(
    width=1024,
    height=768,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

DESKTOP_MEDIUM_OPTIONS = RenderOptions(
    width=1366,
    height=768,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

DESKTOP_LARGE_OPTIONS = RenderOptions(
    width=1920,
    height=1080,
    format="png",
    quality=95,
    device_scale_factor=1.0
)

DESKTOP_4K_OPTIONS = RenderOptions(
    width=3840,
    height=2160,
    format="png",
    quality=95,
    device_scale_factor=1.0
)

# Quality Variations
LOW_QUALITY_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=60,
    device_scale_factor=1.0
)

MEDIUM_QUALITY_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=80,
    device_scale_factor=1.0
)

HIGH_QUALITY_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=95,
    device_scale_factor=1.0
)

MAXIMUM_QUALITY_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=100,
    device_scale_factor=1.0
)

# Performance Testing Options
PERFORMANCE_SMALL_OPTIONS = RenderOptions(
    width=200,
    height=150,
    format="png",
    quality=70,
    device_scale_factor=1.0
)

PERFORMANCE_MEDIUM_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="png",
    quality=80,
    device_scale_factor=1.0
)

PERFORMANCE_LARGE_OPTIONS = RenderOptions(
    width=2560,
    height=1440,
    format="png",
    quality=85,
    device_scale_factor=1.0
)

# Edge Case Options
MINIMAL_SIZE_OPTIONS = RenderOptions(
    width=1,
    height=1,
    format="png",
    quality=50,
    device_scale_factor=1.0
)

SQUARE_OPTIONS = RenderOptions(
    width=600,
    height=600,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

WIDE_ASPECT_OPTIONS = RenderOptions(
    width=1600,
    height=400,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

TALL_ASPECT_OPTIONS = RenderOptions(
    width=400,
    height=1600,
    format="png",
    quality=90,
    device_scale_factor=1.0
)

# Format Variations (for future support)
WEBP_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="webp",
    quality=85,
    device_scale_factor=1.0
)

JPEG_OPTIONS = RenderOptions(
    width=800,
    height=600,
    format="jpeg",
    quality=85,
    device_scale_factor=1.0
)

# Custom User Agent Options
CHROME_OPTIONS = RenderOptions(
    width=1280,
    height=720,
    format="png",
    quality=90,
    device_scale_factor=1.0,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

FIREFOX_OPTIONS = RenderOptions(
    width=1280,
    height=720,
    format="png",
    quality=90,
    device_scale_factor=1.0,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
)

SAFARI_OPTIONS = RenderOptions(
    width=1280,
    height=720,
    format="png",
    quality=90,
    device_scale_factor=1.0,
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
)

# Collections for easy access
MOBILE_DEVICE_OPTIONS = {
    "iphone_portrait": MOBILE_PORTRAIT_OPTIONS,
    "iphone_landscape": MOBILE_LANDSCAPE_OPTIONS,
    "ipad": TABLET_OPTIONS
}

DESKTOP_DEVICE_OPTIONS = {
    "small": DESKTOP_SMALL_OPTIONS,
    "medium": DESKTOP_MEDIUM_OPTIONS,
    "large": DESKTOP_LARGE_OPTIONS,
    "4k": DESKTOP_4K_OPTIONS
}

QUALITY_OPTIONS = {
    "low": LOW_QUALITY_OPTIONS,
    "medium": MEDIUM_QUALITY_OPTIONS,
    "high": HIGH_QUALITY_OPTIONS,
    "maximum": MAXIMUM_QUALITY_OPTIONS
}

PERFORMANCE_OPTIONS = {
    "small": PERFORMANCE_SMALL_OPTIONS,
    "medium": PERFORMANCE_MEDIUM_OPTIONS,
    "large": PERFORMANCE_LARGE_OPTIONS
}

BROWSER_OPTIONS = {
    "chrome": CHROME_OPTIONS,
    "firefox": FIREFOX_OPTIONS,
    "safari": SAFARI_OPTIONS
}

ALL_RENDER_OPTIONS = {
    "basic": BASIC_RENDER_OPTIONS,
    "small": SMALL_RENDER_OPTIONS,
    "large": LARGE_RENDER_OPTIONS,
    "high_dpi": HIGH_DPI_RENDER_OPTIONS,
    "retina": RETINA_RENDER_OPTIONS,
    "mobile_portrait": MOBILE_PORTRAIT_OPTIONS,
    "mobile_landscape": MOBILE_LANDSCAPE_OPTIONS,
    "tablet": TABLET_OPTIONS,
    "desktop_small": DESKTOP_SMALL_OPTIONS,
    "desktop_medium": DESKTOP_MEDIUM_OPTIONS,
    "desktop_large": DESKTOP_LARGE_OPTIONS,
    "desktop_4k": DESKTOP_4K_OPTIONS,
    "low_quality": LOW_QUALITY_OPTIONS,
    "medium_quality": MEDIUM_QUALITY_OPTIONS,
    "high_quality": HIGH_QUALITY_OPTIONS,
    "maximum_quality": MAXIMUM_QUALITY_OPTIONS,
    "minimal_size": MINIMAL_SIZE_OPTIONS,
    "square": SQUARE_OPTIONS,
    "wide_aspect": WIDE_ASPECT_OPTIONS,
    "tall_aspect": TALL_ASPECT_OPTIONS,
    "chrome": CHROME_OPTIONS,
    "firefox": FIREFOX_OPTIONS,
    "safari": SAFARI_OPTIONS
}

def get_render_options(name: str) -> RenderOptions:
    """Get render options by name."""
    return ALL_RENDER_OPTIONS.get(name, BASIC_RENDER_OPTIONS)

def get_mobile_options():
    """Get all mobile device render options."""
    return MOBILE_DEVICE_OPTIONS

def get_desktop_options():
    """Get all desktop render options."""
    return DESKTOP_DEVICE_OPTIONS

def get_quality_options():
    """Get all quality render options."""
    return QUALITY_OPTIONS

def get_performance_options():
    """Get all performance testing render options."""
    return PERFORMANCE_OPTIONS

def get_browser_options():
    """Get all browser-specific render options."""
    return BROWSER_OPTIONS

def create_custom_options(width: int, height: int, quality: int = 90, scale: float = 1.0) -> RenderOptions:
    """Create custom render options with specified parameters."""
    return RenderOptions(
        width=width,
        height=height,
        format="png",
        quality=quality,
        device_scale_factor=scale
    )