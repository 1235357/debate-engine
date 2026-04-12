"""FastAPI application for DebateEngine.

Provides REST endpoints for synchronous quick-critique and asynchronous
multi-round debate operations, with health checking and proper error handling.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from debate_engine.api.middleware import RequestLoggingMiddleware, setup_logging
from debate_engine.orchestration import DebateOrchestrator, QuickCritiqueEngine
from debate_engine.providers.config import ProviderConfig
from debate_engine.schemas import (
    ConsensusSchema,
    CritiqueConfigSchema,
    DebateConfigSchema,
    DebateJobSchema,
    JobStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DebateEngine",
    description="Structured Multi-Agent Critique & Consensus Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register middleware
app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Global engine instances (initialized on startup)
# ---------------------------------------------------------------------------

_quick_engine: QuickCritiqueEngine | None = None
_debate_orchestrator: DebateOrchestrator | None = None


def get_quick_engine() -> QuickCritiqueEngine:
    """Return the global QuickCritiqueEngine instance."""
    if _quick_engine is None:
        raise RuntimeError("QuickCritiqueEngine not initialized. Is the server running?")
    return _quick_engine


def get_debate_orchestrator() -> DebateOrchestrator:
    """Return the global DebateOrchestrator instance."""
    if _debate_orchestrator is None:
        raise RuntimeError("DebateOrchestrator not initialized. Is the server running?")
    return _debate_orchestrator


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup() -> None:
    """Initialize engine instances and configure logging on server start."""
    log_level = os.getenv("DEBATE_ENGINE_LOG_LEVEL", "INFO")
    setup_logging(log_level)

    global _quick_engine, _debate_orchestrator

    provider_config = ProviderConfig.from_env()

    _quick_engine = QuickCritiqueEngine(provider_config)
    _debate_orchestrator = DebateOrchestrator(provider_config)

    logger.info(
        "DebateEngine starting: provider=%s model=%s mode=%s",
        provider_config.primary_provider,
        provider_config.primary_model,
        provider_config.mode.value,
    )


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all exception handler for unhandled errors."""
    error_str = str(exc).lower()

    # Classify errors by content
    if "cost" in error_str and ("budget" in error_str or "exceeded" in error_str):
        return JSONResponse(
            status_code=402,
            content={"error": "cost_budget_exceeded", "detail": str(exc)},
        )
    if "timeout" in error_str or "timed out" in error_str:
        return JSONResponse(
            status_code=408,
            content={"error": "timeout", "detail": str(exc)},
        )
    if "unavailable" in error_str or "provider" in error_str:
        return JSONResponse(
            status_code=503,
            content={"error": "provider_unavailable", "detail": str(exc)},
        )

    # Default: internal server error
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )


@app.exception_handler(KeyError)
async def job_not_found_handler(
    request: Request,
    exc: KeyError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns the service status and version. Used by container health checks.
    """
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/v1/quick-critique")
async def quick_critique(
    request: Request,
    body: CritiqueConfigSchema,
) -> Any:
    """Synchronous quick critique endpoint.

    Runs all three agent roles and returns the consensus result.
    P95 latency target: 5-15 seconds.

    **Errors:**
    - 401: API key not configured
    - 402: Cost budget exceeded
    - 408: LLM call timeout
    - 422: Invalid request body
    - 503: LLM provider unavailable
    """
    _validate_api_key(request)

    engine = get_quick_engine()
    consensus = await engine.critique(body)
    return consensus


@app.post("/v1/debate")
async def submit_debate(
    request: Request,
    body: DebateConfigSchema,
) -> dict[str, str]:
    """Submit an asynchronous multi-round debate task.

    Returns a job_id immediately. Use GET /v1/debate/{job_id} to poll status.

    **Errors:**
    - 401: API key not configured
    - 422: Invalid request body
    """
    _validate_api_key(request)

    orchestrator = get_debate_orchestrator()
    job_id = await orchestrator.submit(body)
    return {"job_id": job_id, "status": "PENDING"}


@app.get("/v1/debate/{job_id}")
async def get_debate_status(job_id: str) -> Any:
    """Get the status and result of a debate job.

    **Errors:**
    - 404: Job not found
    """
    orchestrator = get_debate_orchestrator()
    try:
        job = await orchestrator.get_status(job_id)
        return job
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@app.delete("/v1/debate/{job_id}")
async def cancel_debate(job_id: str) -> dict[str, Any]:
    """Cancel a running or pending debate job.

    **Errors:**
    - 404: Job not found
    """
    orchestrator = get_debate_orchestrator()
    try:
        cancelled = await orchestrator.cancel(job_id)
        return {"job_id": job_id, "cancelled": cancelled}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_api_key(request: Request) -> None:
    """Check that at least one LLM API key is configured.

    Raises HTTPException 401 if no keys are found in the environment.
    """
    api_key = request.headers.get("X-API-Key")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # If an explicit API key header is provided, accept it
    # (in production this would validate against a proper auth system)
    if api_key:
        return

    # Otherwise, require at least one provider key in the environment
    if not openai_key and not anthropic_key:
        raise HTTPException(
            status_code=401,
            detail=(
                "No API key provided. Set X-API-Key header or configure "
                "OPENAI_API_KEY / ANTHROPIC_API_KEY environment variables."
            ),
        )
