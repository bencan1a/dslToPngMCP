"""
Render Routes
=============

FastAPI routes for DSL rendering endpoints.
Provides both synchronous and asynchronous rendering capabilities.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from src.core.dsl.parser import parse_dsl
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import generate_png_from_html, PNGGenerationError
from src.core.queue.tasks import submit_render_task, get_task_result
from src.models.schemas import DSLRenderRequest, RenderResponse, PNGResult

router = APIRouter(prefix="/api/v1", tags=["Rendering"])


async def render_dsl_to_png(dsl_data: Dict[str, Any], options: Dict[str, Any]) -> PNGResult:
    """
    Core function to render DSL to PNG.
    Used by integration tests and route handlers.

    Args:
        dsl_data: DSL document data
        options: Render options

    Returns:
        PNGResult with generated PNG data
    """
    # Parse DSL
    parse_result = await parse_dsl(str(dsl_data))

    if not parse_result.success:
        raise HTTPException(
            status_code=400, detail=f"DSL parsing failed: {'; '.join(parse_result.errors)}"
        )

    if parse_result.document is None:
        raise HTTPException(status_code=400, detail="DSL parsing resulted in empty document")

    # Generate HTML
    from src.models.schemas import RenderOptions

    render_options = RenderOptions(**options)
    html_content = await generate_html(parse_result.document, render_options)

    # Generate PNG
    png_result = await generate_png_from_html(html_content, render_options)

    return png_result


@router.post("/render")
async def render_sync(request: DSLRenderRequest) -> RenderResponse:
    """Synchronous DSL rendering endpoint."""
    try:
        # Convert string DSL to dict for render_dsl_to_png function
        import json

        try:
            dsl_data = json.loads(request.dsl_content)
        except json.JSONDecodeError:
            dsl_data = {"content": request.dsl_content}

        # Handle options
        options_dict = {}
        if request.options:
            options_dict = request.options.model_dump()

        png_result = await render_dsl_to_png(dsl_data, options_dict)
        return RenderResponse(
            success=True, png_result=png_result, error=None, processing_time=0.0  # Placeholder
        )
    except PNGGenerationError as e:
        # Browser pool errors will be handled by the main exception handler
        # but we can also handle them here for consistency
        error_message = str(e)
        if "Browser pool not initialized" in error_message:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Browser pool is not available",
                    "error_code": "BROWSER_POOL_NOT_INITIALIZED",
                    "details": {"message": error_message},
                },
            )
        elif "Browser pool initialization failed" in error_message:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Browser pool initialization failed",
                    "error_code": "BROWSER_POOL_INITIALIZATION_FAILED",
                    "details": {"message": error_message},
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "PNG generation failed",
                    "error_code": "PNG_GENERATION_ERROR",
                    "details": {"message": error_message},
                },
            )
    except Exception as e:
        return RenderResponse(success=False, png_result=None, error=str(e), processing_time=0.0)


@router.post("/render/async")
async def render_async(request: DSLRenderRequest) -> dict[str, Any]:
    """Asynchronous DSL rendering endpoint."""
    task_id = await submit_render_task(request)
    return {"task_id": task_id, "status": "submitted", "estimated_completion": None}


@router.get("/render/async/{task_id}")
async def get_async_status(task_id: str) -> dict[str, Any]:
    """Get async task status endpoint."""
    """Get async render task status."""
    result = await get_task_result(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"task_id": task_id, "status": "completed", "result": result}
