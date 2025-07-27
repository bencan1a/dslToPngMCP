#!/usr/bin/env python3
"""
Direct MCP Tool Test - Isolation Testing Script

This script tests the MCP server tools directly, bypassing all HTTP/SSE infrastructure
to validate if the issue is in the core DSL parsing and rendering logic.

Purpose: Determine if the 'NoneType' error is in the MCP tools themselves
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            "layout": {
                "x": 150,
                "y": 80,
                "width": 100,
                "height": 40
            },
            "style": {
                "background": "#007bff",
                "color": "white",
                "fontSize": 16,
                "fontWeight": "bold",
                "borderRadius": "8px"
            },
            "label": "Click Me!",
            "onClick": "handleClick()"
        }
    ],
    "css": ".dsl-button:hover { transform: scale(1.05); transition: transform 0.2s; }"
}


async def test_mcp_server_direct():
    """Test MCP server initialization and tool access"""
    print("\n" + "="*60)
    print("TESTING: MCP Server Direct Initialization")
    print("="*60)
    
    try:
        from src.mcp_server.server import DSLToPNGMCPServer
        
        logger.info("Creating MCP Server...")
        server = DSLToPNGMCPServer()
        
        logger.info(f"✓ Server created: {type(server)}")
        
        # Test getting tools list
        logger.info("Testing get_tools method...")
        tools = await server.get_tools()
        logger.info(f"✓ Available tools: {[tool.name for tool in tools]}")
        
        # Look for render_ui_mockup tool
        render_tool = None
        for tool in tools:
            if tool.name == "render_ui_mockup":
                render_tool = tool
                break
        
        if render_tool:
            logger.info("✓ render_ui_mockup tool found")
            logger.info(f"  Description: {render_tool.description}")
            logger.info(f"  Input schema keys: {list(render_tool.inputSchema.get('properties', {}).keys())}")
        else:
            logger.error("❌ render_ui_mockup tool not found!")
        
        return server
        
    except Exception as e:
        logger.error(f"❌ Error in MCP server test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_mcp_tool_call_direct():
    """Test calling render_ui_mockup tool directly through MCP server"""
    print("\n" + "="*60)
    print("TESTING: MCP Tool Call Direct")
    print("="*60)
    
    try:
        from src.mcp_server.server import DSLToPNGMCPServer
        
        logger.info("Creating MCP Server for tool call...")
        server = DSLToPNGMCPServer()
        
        # Prepare arguments exactly as they would come from SSE bridge
        arguments = {
            "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
            "width": 400,
            "height": 200,
            "async_mode": False,
            "options": {
                "width": 400,
                "height": 200,
                "device_scale_factor": 1.0,
                "wait_for_load": True,
                "full_page": False,
                "optimize_png": True,
                "timeout": 30,
                "block_resources": False,
                "transparent_background": False
            }
        }
        
        logger.info("Calling render_ui_mockup tool...")
        logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        # Call the tool
        result = await server.call_tool("render_ui_mockup", arguments)
        
        logger.info(f"Tool result type: {type(result)}")
        logger.info(f"Tool result length: {len(result) if result else 'None'}")
        
        if result is None:
            logger.error("❌ MCP tool returned None - FOUND NONETYPE SOURCE!")
            return None
        
        if result and len(result) > 0:
            first_result = result[0]
            logger.info(f"First result type: {type(first_result)}")
            logger.info(f"First result: {first_result}")
            
            if hasattr(first_result, 'text'):
                try:
                    parsed_result = json.loads(first_result.text)
                    logger.info(f"✓ Parsed result keys: {list(parsed_result.keys())}")
                    
                    if parsed_result.get('success'):
                        logger.info("✓ Tool execution reported success")
                    else:
                        logger.error(f"❌ Tool execution failed: {parsed_result.get('error')}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse result as JSON: {e}")
                    logger.info(f"Raw result text: {first_result.text[:200]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in MCP tool call test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_mcp_tool_handler_direct():
    """Test the internal _handle_render_ui_mockup method directly"""
    print("\n" + "="*60)
    print("TESTING: MCP Tool Handler Direct")
    print("="*60)
    
    try:
        from src.mcp_server.server import DSLToPNGMCPServer
        
        logger.info("Creating MCP Server for handler test...")
        server = DSLToPNGMCPServer()
        
        # Prepare arguments
        arguments = {
            "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
            "width": 400,
            "height": 200,
            "async_mode": False,
            "options": {
                "width": 400,
                "height": 200,
                "device_scale_factor": 1.0,
                "wait_for_load": True,
                "full_page": False,
                "optimize_png": True,
                "timeout": 30,
                "block_resources": False,
                "transparent_background": False
            }
        }
        
        logger.info("Calling _handle_render_ui_mockup directly...")
        
        # Call the internal handler directly
        result = await server._handle_render_ui_mockup(arguments)
        
        logger.info(f"Handler result type: {type(result)}")
        logger.info(f"Handler result length: {len(result) if result else 'None'}")
        
        if result is None:
            logger.error("❌ MCP handler returned None - FOUND NONETYPE SOURCE!")
            return None
        
        if result and len(result) > 0:
            first_result = result[0]
            logger.info(f"✓ Handler returned: {type(first_result)}")
            
            if hasattr(first_result, 'text'):
                try:
                    parsed_result = json.loads(first_result.text)
                    logger.info(f"✓ Handler result success: {parsed_result.get('success')}")
                    
                    if not parsed_result.get('success'):
                        logger.error(f"❌ Handler error: {parsed_result.get('error')}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse handler result: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in MCP handler test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_individual_mcp_steps():
    """Test each step of the MCP rendering process individually"""
    print("\n" + "="*60)
    print("TESTING: Individual MCP Rendering Steps")
    print("="*60)
    
    try:
        # Step 1: Test DSL parsing
        logger.info("Step 1: Testing DSL parsing...")
        from src.core.dsl.parser import parse_dsl
        
        dsl_content = json.dumps(SIMPLE_BUTTON_DSL)
        parse_result = await parse_dsl(dsl_content)
        
        logger.info(f"Parse result type: {type(parse_result)}")
        logger.info(f"Parse success: {parse_result.success}")
        logger.info(f"Parse document: {type(parse_result.document)}")
        
        if not parse_result.success:
            logger.error(f"❌ DSL parsing failed: {parse_result.errors}")
            return None
        
        if parse_result.document is None:
            logger.error("❌ DSL parsing returned None document - FOUND NONETYPE SOURCE!")
            return None
        
        logger.info("✓ DSL parsing successful")
        
        # Step 2: Test HTML generation
        logger.info("Step 2: Testing HTML generation...")
        from src.core.rendering.html_generator import generate_html
        from src.models.schemas import RenderOptions
        
        render_options = RenderOptions(
            width=400,
            height=200,
            device_scale_factor=1.0,
            wait_for_load=True,
            full_page=False,
            optimize_png=True,
            timeout=30,
            block_resources=False,
            transparent_background=False
        )
        
        html_content = await generate_html(parse_result.document, render_options)
        
        logger.info(f"HTML content type: {type(html_content)}")
        logger.info(f"HTML content length: {len(html_content) if html_content else 'None'}")
        
        if html_content is None:
            logger.error("❌ HTML generation returned None - FOUND NONETYPE SOURCE!")
            return None
        
        logger.info("✓ HTML generation successful")
        
        # Step 3: Test PNG generation (with mock browser pool)
        logger.info("Step 3: Testing PNG generation...")
        try:
            from src.core.rendering.png_generator import generate_png_from_html
            
            # This will likely fail due to browser dependencies, but we can see how far it gets
            png_result = await generate_png_from_html(html_content, render_options)
            
            logger.info(f"PNG result type: {type(png_result)}")
            
            if png_result is None:
                logger.error("❌ PNG generation returned None - FOUND NONETYPE SOURCE!")
                return None
            
            logger.info("✓ PNG generation successful")
            
        except Exception as png_error:
            logger.warning(f"⚠ PNG generation failed (expected): {png_error}")
            logger.info("This is expected in isolation test without browser infrastructure")
        
        return {
            "parse_result": parse_result,
            "html_content": html_content,
            "steps_completed": ["parse", "html"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error in individual steps test: {e}")
        logger.exception("Full traceback:")
        return None


async def main():
    """Run all direct MCP tool tests"""
    print("🔍 DIRECT MCP TOOL ISOLATION TESTS")
    print("Purpose: Test MCP tools without any HTTP/SSE infrastructure")
    print("Goal: Determine if NoneType error is in core MCP tool logic")
    
    results = {}
    
    # Test 1: MCP Server Direct
    results['mcp_server'] = await test_mcp_server_direct()
    
    # Test 2: MCP Tool Call Direct
    results['mcp_tool_call'] = await test_mcp_tool_call_direct()
    
    # Test 3: MCP Handler Direct
    results['mcp_handler'] = await test_mcp_tool_handler_direct()
    
    # Test 4: Individual Steps
    results['individual_steps'] = await test_individual_mcp_steps()
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result is not None and result is not False else "❌ FAIL"
        print(f"{test_name:20} {status}")
        
        if result is None:
            print(f"  → {test_name} returned None (potential NoneType source)")
    
    # Analysis
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    
    if results['mcp_server'] is None:
        print("🎯 ISSUE FOUND: MCP Server creation failed")
        print("   The NoneType error may be in MCP server initialization")
    elif results['mcp_tool_call'] is None:
        print("🎯 ISSUE FOUND: MCP Tool call returned None")
        print("   The NoneType error is in the MCP tool execution layer")
    elif results['mcp_handler'] is None:
        print("🎯 ISSUE FOUND: MCP Handler returned None")
        print("   The NoneType error is in the internal handler logic")
    elif results['individual_steps'] is None:
        print("🎯 ISSUE FOUND: Individual rendering steps failed")
        print("   The NoneType error is in DSL parsing, HTML generation, or PNG generation")
    else:
        print("✓ All MCP tool components passed direct testing")
        print("  The NoneType error is likely in the SSE/HTTP infrastructure layer")
        
        # Additional analysis if individual steps passed
        if isinstance(results['individual_steps'], dict):
            steps = results['individual_steps']
            if steps.get('parse_result') and not steps['parse_result'].success:
                print("  → DSL parsing had errors")
            elif steps.get('html_content') is None:
                print("  → HTML generation returned None")
            else:
                print("  → Core rendering pipeline works, issue is in infrastructure")


if __name__ == "__main__":
    asyncio.run(main())