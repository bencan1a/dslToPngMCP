#!/usr/bin/env python3
"""
End-to-End SSE Pipeline Test Script
===================================

Tests the complete SSE pipeline by:
1. Starting the SSE server
2. Connecting via SSE
3. Submitting a DSL for rendering
4. Receiving real-time progress updates
5. Saving the final PNG with timestamp

Usage:
    python test_e2e_sse.py <dsl_input_file>

Example:
    python test_e2e_sse.py examples/simple_button.json
"""

print("🔧 DEBUG: Script started, beginning imports...")

import sys

print("🔧 DEBUG: sys imported")

import os

print("🔧 DEBUG: os imported")

import json

print("🔧 DEBUG: json imported")

import asyncio

print("🔧 DEBUG: asyncio imported")

import aiohttp

print("🔧 DEBUG: aiohttp imported")

import time

print("🔧 DEBUG: time imported")

from datetime import datetime

print("🔧 DEBUG: datetime imported")

from pathlib import Path

print("🔧 DEBUG: Path imported")

import argparse

print("🔧 DEBUG: argparse imported")

print("🔧 DEBUG: All imports completed successfully")

# Test configuration
SSE_ENDPOINT = "http://localhost/sse/connect"
RENDER_ENDPOINT = "http://localhost/sse/render"
API_KEY = "test-api-key-123"  # For testing
OUTPUT_DIR = Path("test-results")


async def connect_sse(session, client_id=None):
    """Connect to SSE endpoint and return the event stream."""
    headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache", "X-API-Key": API_KEY}

    params = {}
    if client_id:
        params["client_id"] = client_id

    print(f"📡 Connecting to SSE endpoint: {SSE_ENDPOINT}")

    try:
        response = await session.get(SSE_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()

        connection_id = response.headers.get("X-Connection-ID")
        print(f"✅ SSE connection established. Connection ID: {connection_id}")

        return response, connection_id
    except Exception as e:
        print(f"❌ Failed to connect to SSE: {e}")
        raise


async def parse_sse_events(response):
    """Parse SSE events from the response stream."""
    buffer = ""

    async for data in response.content.iter_chunked(1024):
        buffer += data.decode("utf-8")

        while "\n\n" in buffer:
            event_data, buffer = buffer.split("\n\n", 1)

            if event_data.strip():
                event = parse_sse_event(event_data)
                yield event


def parse_sse_event(event_data):
    """Parse a single SSE event."""
    event = {"id": None, "event": None, "data": None, "retry": None}

    for line in event_data.split("\n"):
        if ":" in line:
            field, value = line.split(":", 1)
            field = field.strip()
            value = value.strip()

            if field in event:
                event[field] = value

    # Parse JSON data if present
    if event["data"]:
        try:
            event["data"] = json.loads(event["data"])
        except json.JSONDecodeError:
            pass  # Keep as string if not valid JSON

    return event


async def submit_render_request_fire_and_forget(session, connection_id, dsl_content, options=None):
    """Submit a render request via SSE using fire-and-forget pattern."""
    if options is None:
        options = {
            "width": 800,
            "height": 600,
            "device_scale_factor": 1.0,
            "optimize_png": True,
            "timeout": 30,
        }

    # Format payload to match SSERenderRequest model
    payload = {
        "dsl_content": dsl_content,
        "options": options,
        "connection_id": connection_id,
        "request_id": f"test-{int(time.time())}",
        "progress_updates": True,
    }

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    print(f"🚀 Submitting render request to: {RENDER_ENDPOINT}")
    print(f"📄 DSL content length: {len(dsl_content)} characters")
    print(f"🔗 Using connection ID: {connection_id}")

    try:
        print(f"🔄 Making fire-and-forget HTTP POST request...")
        # Fire-and-forget: start the request but don't wait for completion
        asyncio.create_task(send_render_request(session, payload, headers))
        print(f"✅ Render request fired, listening for SSE events...")
        return True
    except Exception as e:
        print(f"❌ Failed to submit render request: {e}")
        print(f"📋 Request payload: {payload}")
        raise


async def send_render_request(session, payload, headers):
    """Actually send the render request (runs in background)."""
    import time

    task_start = time.time()
    try:
        print(f"🔧 DEBUG: Background task started at {task_start}, URL: {RENDER_ENDPOINT}")
        print(f"🔧 DEBUG: Background task payload keys: {list(payload.keys())}")

        print(f"🔧 DEBUG: About to create POST request...")
        post_start = time.time()
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for background request

        # Use separate session to avoid connection pool blocking
        print(f"🔧 DEBUG: Creating separate session for POST to avoid connection pool issues...")
        async with aiohttp.ClientSession(timeout=timeout) as post_session:
            async with post_session.post(
                RENDER_ENDPOINT, json=payload, headers=headers
            ) as response:
                post_complete = time.time()
                print(
                    f"📡 Background: Received HTTP response: {response.status} after {post_complete - post_start:.2f}s"
                )
                print(f"🔧 DEBUG: Total task execution time: {post_complete - task_start:.2f}s")
                response_text = await response.text()
                print(f"🔧 DEBUG: Response content: {response_text[:200]}...")
                if response.status == 202:  # Accepted
                    print(f"✅ Background: Render request accepted by server")
                else:
                    response.raise_for_status()
    except Exception as e:
        error_time = time.time()
        print(
            f"❌ Background: Render request failed after {error_time - task_start:.2f}s: {type(e).__name__}: {e}"
        )
        import traceback

        print(f"🔧 DEBUG: Full traceback: {traceback.format_exc()}")


def save_png_output(png_data, filename_prefix="sse_test"):
    """Save PNG data to timestamped file in test-results directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.png"
    filepath = OUTPUT_DIR / filename

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Decode base64 if needed
    import base64

    if isinstance(png_data, str):
        try:
            png_bytes = base64.b64decode(png_data)
        except:
            png_bytes = png_data.encode()
    else:
        png_bytes = png_data

    with open(filepath, "wb") as f:
        f.write(png_bytes)

    print(f"💾 PNG saved to: {filepath}")
    print(f"📊 File size: {len(png_bytes)} bytes")
    return filepath


async def test_e2e_sse_pipeline(dsl_file_path):
    """Test the complete E2E SSE pipeline."""
    print(f"🧪 Starting E2E SSE Pipeline Test")
    print(f"📁 Input DSL file: {dsl_file_path}")
    print(f"📂 Output directory: {OUTPUT_DIR}")
    print("-" * 60)

    # Read DSL content
    try:
        with open(dsl_file_path, "r") as f:
            dsl_content = f.read()
        print(f"✅ DSL file loaded successfully")
    except Exception as e:
        print(f"❌ Failed to read DSL file: {e}")
        return False

    # Validate JSON/YAML
    try:
        if dsl_file_path.endswith(".json"):
            json.loads(dsl_content)
        print(f"✅ DSL content validation passed")
    except Exception as e:
        print(f"⚠️  DSL validation warning: {e}")

    timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # Step 1: Connect to SSE
            print("🔧 DEBUG: About to connect to SSE endpoint...")
            response, connection_id = await connect_sse(session, "e2e-test-client")
            print(f"🔧 DEBUG: SSE connection successful, connection_id: {connection_id}")

            # Wait for connection to be fully registered in Redis
            print("⏳ Waiting for connection to be fully established...")
            await asyncio.sleep(3)

            # Step 2: Submit render request (fire-and-forget)
            print("🔄 About to submit render request...")
            start_time = time.time()
            await submit_render_request_fire_and_forget(session, connection_id, dsl_content)
            elapsed = time.time() - start_time
            print(f"⏱️  Render request fired in {elapsed:.2f} seconds")

            # Step 3: Listen for SSE events
            print("\n📻 Listening for SSE events...")
            print("-" * 40)

            events_received = []
            render_completed = False
            png_data = None

            # Add timeout for SSE listening (15 seconds to confirm diagnosis)
            timeout_seconds = 15
            start_time = time.time()
            print(f"⏰ Setting timeout for SSE listening: {timeout_seconds} seconds")

            async for event in parse_sse_events(response):
                # Check timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout_seconds:
                    print(f"⏰ TIMEOUT: SSE listening timed out after {elapsed_time:.1f} seconds")
                    print(f"🔍 DIAGNOSIS CONFIRMED: Script hangs waiting for SSE response!")
                    print(f"📊 Events received before timeout: {len(events_received)}")
                    break

                events_received.append(event)

                event_type = event.get("event")
                data = event.get("data", {})

                if event_type == "connection.opened":
                    print(f"🔗 Connection opened: {data.get('message', 'N/A')}")

                elif event_type == "connection.heartbeat":
                    print(f"💓 Heartbeat: {data.get('server_time', 'N/A')}")

                elif event_type == "render.started":
                    print(f"🚀 Render started: {data.get('message', 'N/A')}")

                elif event_type == "render.progress":
                    progress = data.get("progress", 0)
                    message = data.get("message", "Processing...")
                    stage = data.get("stage", "unknown")
                    print(f"⏳ Progress: {progress}% - {message} [{stage}]")

                elif event_type == "render.completed":
                    print(f"✅ Render completed: {data.get('message', 'N/A')}")

                    # Extract PNG data
                    result = data.get("result", {})
                    if "png_data" in result:
                        png_data = result["png_data"]
                    elif "png_result" in result:
                        png_result = result["png_result"]
                        png_data = (
                            png_result.get("png_data")
                            or png_result.get("data")
                            or png_result.get("base64_data")
                        )

                    render_completed = True
                    break

                elif event_type == "render.failed":
                    error = data.get("error", "Unknown error")
                    print(f"❌ Render failed: {error}")
                    break

                elif event_type == "connection.error":
                    error_msg = data.get("error_message", "Unknown error")
                    print(f"🚫 Connection error: {error_msg}")
                    break

                # Timeout protection
                if len(events_received) > 100:
                    print("⏰ Event limit reached, stopping...")
                    break

            print("-" * 40)
            print(f"📊 Total events received: {len(events_received)}")

            # Step 4: Save results
            if render_completed and png_data:
                filename_prefix = Path(dsl_file_path).stem
                output_file = save_png_output(png_data, filename_prefix)
                print(f"\n🎉 E2E SSE Pipeline Test SUCCESSFUL!")
                print(f"📄 Output file: {output_file}")
                return True
            else:
                print(f"\n❌ E2E SSE Pipeline Test FAILED!")
                print(f"🔍 Render completed: {render_completed}")
                print(f"🔍 PNG data received: {png_data is not None}")
                return False

        except asyncio.TimeoutError:
            print(f"\n⏰ Test timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
            return False


def main():
    """Main entry point."""
    print("🔧 DEBUG: Script starting, parsing arguments...")
    parser = argparse.ArgumentParser(description="Test E2E SSE Pipeline")
    parser.add_argument("dsl_file", help="Path to DSL input file (JSON or YAML)")
    parser.add_argument("--server", default="localhost:8000", help="Server host:port")

    print("🔧 DEBUG: Parsing command line arguments...")
    args = parser.parse_args()
    print(f"🔧 DEBUG: Arguments parsed - DSL file: {args.dsl_file}, Server: {args.server}")

    # Update endpoints if custom server provided
    if args.server != "localhost:8000":
        global SSE_ENDPOINT, RENDER_ENDPOINT
        base_url = f"http://{args.server}"
        SSE_ENDPOINT = f"{base_url}/sse/connect"
        RENDER_ENDPOINT = f"{base_url}/sse/render"
        print(f"🔧 DEBUG: Endpoints updated - SSE: {SSE_ENDPOINT}, Render: {RENDER_ENDPOINT}")

    # Verify DSL file exists
    print(f"🔧 DEBUG: Checking if DSL file exists: {args.dsl_file}")
    if not Path(args.dsl_file).exists():
        print(f"❌ DSL file not found: {args.dsl_file}")
        sys.exit(1)
    print("🔧 DEBUG: DSL file exists, starting async execution...")

    try:
        print("🔧 DEBUG: About to call asyncio.run...")
        success = asyncio.run(test_e2e_sse_pipeline(args.dsl_file))
        print(f"🔧 DEBUG: asyncio.run completed, success: {success}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"🔧 DEBUG: Exception in main: {e}")
        raise


if __name__ == "__main__":
    main()
