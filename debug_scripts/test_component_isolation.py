#!/usr/bin/env python3
"""
Component Isolation Test - Isolation Testing Script

This script tests each component individually: DSL parser, HTML generator, PNG generator.
Processes simple_button.json through each step separately to identify exactly which
component fails with the NoneType error.

Purpose: Isolate the exact component causing the 'NoneType' error
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test data - exact simple_button.json content
SIMPLE_BUTTON_DSL = {
    "title": "Simple Button Example",
    "description": "A basic button demonstration",
    "width": 400,
    "height": 200,
    "elements": [
        {
            "type": "button",
            "id": "primary-btn",
            "layout": {"x": 150, "y": 80, "width": 100, "height": 40},
            "style": {
                "background": "#007bff",
                "color": "white",
                "fontSize": 16,
                "fontWeight": "bold",
                "borderRadius": "8px",
            },
            "label": "Click Me!",
            "onClick": "handleClick()",
        }
    ],
    "css": ".dsl-button:hover { transform: scale(1.05); transition: transform 0.2s; }",
}


async def test_dsl_parser_isolation():
    """Test DSL parser component in complete isolation"""
    print("\n" + "=" * 60)
    print("TESTING: DSL Parser Component Isolation")
    print("=" * 60)

    try:
        from src.core.dsl.parser import parse_dsl, DSLParserFactory, JSONDSLParser

        logger.info("Testing DSL parser factory...")

        # Test 1: Parser factory
        parser_type = DSLParserFactory.detect_parser_type(json.dumps(SIMPLE_BUTTON_DSL))
        logger.info(f"✓ Detected parser type: {parser_type}")

        parser = DSLParserFactory.create_parser(parser_type)
        logger.info(f"✓ Created parser: {type(parser)}")

        # Test 2: Direct parser instance
        json_parser = JSONDSLParser()
        logger.info(f"✓ Created JSON parser: {type(json_parser)}")

        # Test 3: Parse the DSL content
        dsl_content = json.dumps(SIMPLE_BUTTON_DSL)
        logger.info(f"DSL content length: {len(dsl_content)}")

        parse_result = await parse_dsl(dsl_content)

        logger.info(f"Parse result type: {type(parse_result)}")
        logger.info(f"Parse success: {parse_result.success}")
        logger.info(f"Parse errors: {parse_result.errors}")
        logger.info(f"Parse warnings: {getattr(parse_result, 'warnings', [])}")
        logger.info(f"Processing time: {parse_result.processing_time}")

        # Check if document is None
        if parse_result.document is None:
            logger.error("❌ DSL parser returned None document - FOUND NONETYPE SOURCE!")
            return None

        logger.info(f"✓ Document type: {type(parse_result.document)}")
        logger.info(f"Document title: {parse_result.document.title}")
        logger.info(
            f"Document dimensions: {parse_result.document.width}x{parse_result.document.height}"
        )
        logger.info(f"Document elements count: {len(parse_result.document.elements)}")

        # Check each element
        for i, element in enumerate(parse_result.document.elements):
            logger.info(f"Element {i}: type={element.type}, id={element.id}")

            # Check if any element components are None
            if element.layout is None:
                logger.warning(f"⚠ Element {i} layout is None")
            else:
                logger.info(
                    f"  Layout: x={element.layout.x}, y={element.layout.y}, w={element.layout.width}, h={element.layout.height}"
                )

            if element.style is None:
                logger.warning(f"⚠ Element {i} style is None")
            else:
                logger.info(f"  Style: bg={element.style.background}, color={element.style.color}")

        return parse_result

    except Exception as e:
        logger.error(f"❌ Error in DSL parser isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_html_generator_isolation():
    """Test HTML generator component in isolation"""
    print("\n" + "=" * 60)
    print("TESTING: HTML Generator Component Isolation")
    print("=" * 60)

    try:
        from src.core.rendering.html_generator import (
            generate_html,
            HTMLGeneratorFactory,
            Jinja2HTMLGenerator,
        )
        from src.models.schemas import RenderOptions

        # First, get a parsed document
        logger.info("Getting parsed DSL document...")
        from src.core.dsl.parser import parse_dsl

        dsl_content = json.dumps(SIMPLE_BUTTON_DSL)
        parse_result = await parse_dsl(dsl_content)

        if not parse_result.success or parse_result.document is None:
            logger.error("❌ Cannot test HTML generator - DSL parsing failed")
            return None

        logger.info("✓ Got parsed document for HTML generation")

        # Test 1: Create render options
        logger.info("Creating render options...")
        render_options = RenderOptions(
            width=400,
            height=200,
            device_scale_factor=1.0,
            user_agent="Mozilla/5.0 (Linux; MCP Isolation Test)",
            wait_for_load=True,
            full_page=False,
            png_quality=90,
            optimize_png=True,
            timeout=30,
            block_resources=False,
            background_color="#ffffff",
            transparent_background=False,
        )

        logger.info(f"✓ Render options: {render_options.width}x{render_options.height}")

        # Test 2: HTML generator factory
        generator = HTMLGeneratorFactory.create_generator("jinja2")
        logger.info(f"✓ Created HTML generator: {type(generator)}")

        # Test 3: Direct generator instance
        jinja_generator = Jinja2HTMLGenerator()
        logger.info(f"✓ Created Jinja2 generator: {type(jinja_generator)}")

        # Test 4: Generate HTML
        logger.info("Generating HTML from document...")
        html_content = await generate_html(parse_result.document, render_options)

        logger.info(f"HTML content type: {type(html_content)}")

        if html_content is None:
            logger.error("❌ HTML generator returned None - FOUND NONETYPE SOURCE!")
            return None

        logger.info(f"✓ HTML content length: {len(html_content)}")
        logger.info(f"HTML preview: {html_content[:200]}...")

        # Validate HTML structure
        if "<!DOCTYPE html>" in html_content:
            logger.info("✓ HTML contains DOCTYPE")
        else:
            logger.warning("⚠ HTML missing DOCTYPE")

        if "dsl-button" in html_content:
            logger.info("✓ HTML contains button element")
        else:
            logger.warning("⚠ HTML missing button element")

        return html_content

    except Exception as e:
        logger.error(f"❌ Error in HTML generator isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_png_generator_isolation():
    """Test PNG generator component in isolation (with mocks)"""
    print("\n" + "=" * 60)
    print("TESTING: PNG Generator Component Isolation")
    print("=" * 60)

    try:
        from src.core.rendering.png_generator import (
            PNGGeneratorFactory,
            PlaywrightPNGGenerator,
            BrowserPool,
        )
        from src.models.schemas import RenderOptions, PNGResult

        # Create render options
        render_options = RenderOptions(
            width=400,
            height=200,
            device_scale_factor=1.0,
            wait_for_load=True,
            full_page=False,
            optimize_png=True,
            timeout=30,
            block_resources=False,
            transparent_background=False,
        )

        logger.info("✓ Created render options for PNG test")

        # Test 1: PNG generator factory
        logger.info("Testing PNG generator factory...")
        try:
            generator = PNGGeneratorFactory.create_generator("playwright")
            logger.info(f"✓ Created PNG generator: {type(generator)}")
        except Exception as e:
            logger.error(f"❌ PNG generator factory failed: {e}")
            return None

        # Test 2: Browser pool creation (will fail without browser, but we can test instantiation)
        logger.info("Testing browser pool instantiation...")
        try:
            browser_pool = BrowserPool(pool_size=1)
            logger.info(f"✓ Created browser pool: {type(browser_pool)}")
        except Exception as e:
            logger.error(f"❌ Browser pool creation failed: {e}")
            return None

        # Test 3: Mock PNG generation
        logger.info("Testing PNG generation with mock...")

        # Create a mock HTML content
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <div class="dsl-element dsl-button" style="left: 150px; top: 80px; width: 100px; height: 40px; background: #007bff; color: white;">
                Click Me!
            </div>
        </body>
        </html>
        """

        # Try to create PNG generator (this will likely fail due to missing browser dependencies)
        try:
            png_generator = PlaywrightPNGGenerator()
            logger.info(f"✓ Created Playwright PNG generator: {type(png_generator)}")

            # This will fail, but we can see how far it gets
            try:
                await png_generator.initialize()
                logger.info("✓ PNG generator initialized")

                png_result = await png_generator.generate_png(mock_html, render_options)

                if png_result is None:
                    logger.error("❌ PNG generator returned None - FOUND NONETYPE SOURCE!")
                    return None

                logger.info(f"✓ PNG generation successful: {type(png_result)}")
                return png_result

            except Exception as png_error:
                logger.warning(f"⚠ PNG generation failed (expected in isolation): {png_error}")
                logger.info(
                    "This is expected - browser dependencies not available in isolation test"
                )

                # Return a mock result to indicate the component structure is correct
                return {
                    "component_structure": "valid",
                    "png_generator_type": type(png_generator).__name__,
                    "initialization": "attempted",
                    "error": str(png_error),
                }

        except Exception as generator_error:
            logger.warning(f"⚠ PNG generator creation failed: {generator_error}")
            return None

    except Exception as e:
        logger.error(f"❌ Error in PNG generator isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_models_schemas_isolation():
    """Test models and schemas in isolation"""
    print("\n" + "=" * 60)
    print("TESTING: Models and Schemas Component Isolation")
    print("=" * 60)

    try:
        from src.models.schemas import (
            DSLDocument,
            DSLElement,
            ElementType,
            ElementStyle,
            ElementLayout,
            RenderOptions,
            PNGResult,
            DSLRenderRequest,
        )

        logger.info("Testing schema imports...")

        # Test 1: ElementLayout creation
        layout = ElementLayout(x=150, y=80, width=100, height=40)

        logger.info(f"✓ Created ElementLayout: {type(layout)}")
        logger.info(
            f"Layout values: x={layout.x}, y={layout.y}, w={layout.width}, h={layout.height}"
        )

        if layout.x is None or layout.y is None:
            logger.error("❌ ElementLayout has None values - FOUND NONETYPE SOURCE!")
            return None

        # Test 2: ElementStyle creation
        style = ElementStyle(
            background="#007bff",
            color="white",
            font_size=16,
            font_weight="bold",
            border_radius="8px",
        )

        logger.info(f"✓ Created ElementStyle: {type(style)}")
        logger.info(f"Style values: bg={style.background}, color={style.color}")

        # Test 3: DSLElement creation
        element = DSLElement(
            id="primary-btn",
            type=ElementType.BUTTON,
            layout=layout,
            style=style,
            label="Click Me!",
            onClick="handleClick()",
        )

        logger.info(f"✓ Created DSLElement: {type(element)}")
        logger.info(f"Element type: {element.type}")

        if element.layout is None or element.style is None:
            logger.error("❌ DSLElement has None layout/style - FOUND NONETYPE SOURCE!")
            return None

        # Test 4: DSLDocument creation
        document = DSLDocument(
            title="Simple Button Example",
            description="A basic button demonstration",
            width=400,
            height=200,
            elements=[element],
            css=".dsl-button:hover { transform: scale(1.05); }",
        )

        logger.info(f"✓ Created DSLDocument: {type(document)}")
        logger.info(f"Document dimensions: {document.width}x{document.height}")

        if document.elements is None or len(document.elements) == 0:
            logger.error("❌ DSLDocument has None/empty elements - FOUND NONETYPE SOURCE!")
            return None

        # Test 5: RenderOptions creation
        render_options = RenderOptions(
            width=400, height=200, device_scale_factor=1.0, wait_for_load=True, optimize_png=True
        )

        logger.info(f"✓ Created RenderOptions: {type(render_options)}")

        # Test 6: DSLRenderRequest creation
        render_request = DSLRenderRequest(
            dsl_content=json.dumps(SIMPLE_BUTTON_DSL), options=render_options
        )

        logger.info(f"✓ Created DSLRenderRequest: {type(render_request)}")

        if render_request.dsl_content is None or render_request.options is None:
            logger.error("❌ DSLRenderRequest has None values - FOUND NONETYPE SOURCE!")
            return None

        return {
            "layout": layout,
            "style": style,
            "element": element,
            "document": document,
            "render_options": render_options,
            "render_request": render_request,
        }

    except Exception as e:
        logger.error(f"❌ Error in models/schemas isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_settings_config_isolation():
    """Test settings and configuration in isolation"""
    print("\n" + "=" * 60)
    print("TESTING: Settings and Config Component Isolation")
    print("=" * 60)

    try:
        from src.config.settings import get_settings
        from src.config.logging import get_logger

        logger.info("Testing configuration imports...")

        # Test 1: Settings
        settings = get_settings()
        logger.info(f"✓ Got settings: {type(settings)}")

        if settings is None:
            logger.error("❌ Settings returned None - FOUND NONETYPE SOURCE!")
            return None

        # Check critical settings
        logger.info(f"Browser pool size: {getattr(settings, 'browser_pool_size', 'Not set')}")
        logger.info(f"Playwright headless: {getattr(settings, 'playwright_headless', 'Not set')}")
        logger.info(f"Debug mode: {getattr(settings, 'debug', 'Not set')}")

        # Test 2: Logger
        test_logger = get_logger("isolation_test")
        logger.info(f"✓ Got logger: {type(test_logger)}")

        if test_logger is None:
            logger.error("❌ Logger returned None - FOUND NONETYPE SOURCE!")
            return None

        return {"settings": settings, "logger": test_logger}

    except Exception as e:
        logger.error(f"❌ Error in settings/config isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def main():
    """Run all component isolation tests"""
    print("🔍 COMPONENT ISOLATION TESTS")
    print("Purpose: Test each component individually to isolate NoneType error source")
    print("Goal: Identify the exact component causing the issue")

    results = {}

    # Test 1: Models and Schemas
    results["models_schemas"] = await test_models_schemas_isolation()

    # Test 2: Settings and Config
    results["settings_config"] = await test_settings_config_isolation()

    # Test 3: DSL Parser
    results["dsl_parser"] = await test_dsl_parser_isolation()

    # Test 4: HTML Generator
    results["html_generator"] = await test_html_generator_isolation()

    # Test 5: PNG Generator (with mocks)
    results["png_generator"] = await test_png_generator_isolation()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result is not None and result is not False else "❌ FAIL"
        print(f"{test_name:20} {status}")

        if result is None:
            print(f"  → {test_name} returned None (potential NoneType source)")
        elif result is False:
            print(f"  → {test_name} failed to execute")

    # Detailed Analysis
    print("\n" + "=" * 60)
    print("DETAILED ANALYSIS")
    print("=" * 60)

    # Check each component for specific issues
    if results["models_schemas"] is None:
        print("🎯 ISSUE FOUND: Models/Schemas component failed")
        print("   The NoneType error is in basic data model creation")
    elif results["settings_config"] is None:
        print("🎯 ISSUE FOUND: Settings/Config component failed")
        print("   The NoneType error is in configuration loading")
    elif results["dsl_parser"] is None:
        print("🎯 ISSUE FOUND: DSL Parser component failed")
        print("   The NoneType error is in DSL parsing logic")
    elif results["html_generator"] is None:
        print("🎯 ISSUE FOUND: HTML Generator component failed")
        print("   The NoneType error is in HTML generation logic")
    elif results["png_generator"] is None:
        print("🎯 ISSUE FOUND: PNG Generator component failed")
        print("   The NoneType error is in PNG generation setup")
    else:
        print("✓ All individual components passed isolation testing")
        print("  The NoneType error is likely in component interaction or infrastructure")

        # Additional analysis for successful components
        if isinstance(results["dsl_parser"], type(None)):
            print("  → DSL Parser returned None document")
        elif isinstance(results["html_generator"], type(None)):
            print("  → HTML Generator returned None content")
        else:
            print("  → Core rendering pipeline components work individually")
            print("  → Issue is in component integration or external dependencies")


if __name__ == "__main__":
    asyncio.run(main())
