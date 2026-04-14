"""FastAPI application for DebateEngine.

Provides REST endpoints for synchronous quick-critique and asynchronous
multi-round debate operations, with health checking and proper error handling.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from debate_engine.api.key_manager import APIKeyManager
from debate_engine.api.middleware import RequestLoggingMiddleware, setup_logging
from debate_engine.orchestration import DebateOrchestrator, QuickCritiqueEngine
from debate_engine.providers.config import ProviderConfig
from debate_engine.schemas import (
    CritiqueConfigSchema,
    DebateConfigSchema,
    TaskType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DebateEngine",
    description="Structured Multi-Agent Critique & Consensus Engine",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register middleware
app.add_middleware(RequestLoggingMiddleware)
# Configure CORS
allow_origins = os.getenv("DEBATE_ENGINE_CORS_ORIGINS", "*").split(",")
allow_origins = [origin.strip() for origin in allow_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)

# ---------------------------------------------------------------------------
# Global engine instances (initialized on startup)
# ---------------------------------------------------------------------------

_quick_engine: QuickCritiqueEngine | None = None
_debate_orchestrator: DebateOrchestrator | None = None
_key_manager: APIKeyManager | None = None


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


def get_key_manager() -> APIKeyManager:
    """Return the global APIKeyManager instance."""
    if _key_manager is None:
        raise RuntimeError("APIKeyManager not initialized. Is the server running?")
    return _key_manager


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def _maybe_await(callable, *args, **kwargs):
    """Await a callable if it's coroutine, otherwise call it directly."""
    result = callable(*args, **kwargs)
    if hasattr(result, "__await__"):
        result = await result
    return result


def load_api_keys() -> list[str]:
    """Load API keys from environment variables."""
    keys = []

    # Load primary API keys
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        keys.append(google_key)

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        keys.append(groq_key)

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        keys.append(nvidia_key)

    # Load additional NVIDIA API keys
    for i in range(1, 11):
        key = os.getenv(f"NVIDIA_API_KEY_{i}")
        if key:
            keys.append(key)

    return keys


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    """Initialize engine instances and configure logging on server start."""
    log_level = os.getenv("DEBATE_ENGINE_LOG_LEVEL", "INFO")
    setup_logging(log_level)

    global _quick_engine, _debate_orchestrator, _key_manager

    provider_config = ProviderConfig.from_env()

    # Initialize API key manager
    api_keys = load_api_keys()
    if api_keys:
        _key_manager = APIKeyManager(api_keys)
        logger.info(f"APIKeyManager initialized with {len(api_keys)} keys")
    else:
        logger.warning("No API keys found for APIKeyManager")

    _quick_engine = QuickCritiqueEngine(provider_config, key_manager=_key_manager)
    _debate_orchestrator = DebateOrchestrator(provider_config, key_manager=_key_manager)

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
    await _maybe_await(_validate_api_key, request)

    engine = get_quick_engine()
    consensus = await _maybe_await(engine.critique, body)
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
    await _maybe_await(_validate_api_key, request)

    orchestrator = get_debate_orchestrator()
    job_id = await _maybe_await(orchestrator.submit, body)
    return {"job_id": job_id, "status": "PENDING"}


@app.get("/v1/debate/{job_id}")
async def get_debate_status(job_id: str) -> Any:
    """Get the status and result of a debate job.

    **Errors:**
    - 404: Job not found
    """
    orchestrator = get_debate_orchestrator()
    try:
        job = await _maybe_await(orchestrator.get_status, job_id)
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
        cancelled = await _maybe_await(orchestrator.cancel, job_id)
        return {"job_id": job_id, "cancelled": cancelled}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


# ---------------------------------------------------------------------------
# Additional endpoints (compatible with api_server.py)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_compat():
    """Health check endpoint (compatible with api_server.py)."""
    stats = {}
    try:
        key_manager = get_key_manager()
        stats = key_manager.get_stats()
    except RuntimeError:
        pass
    return {"status": "healthy", "version": "0.2.0", "api_keys": stats}


@app.get("/api/stats")
async def get_stats():
    """Get API key usage statistics."""
    try:
        key_manager = get_key_manager()
        return key_manager.get_stats()
    except RuntimeError:
        raise HTTPException(status_code=500, detail="API key manager not initialized")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = "minimaxai/minimax-m2.7"


class CritiqueRequest(BaseModel):
    content: str
    task_type: str = "CODE_REVIEW"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint using DebateEngine with full multi-agent transparency."""
    try:
        # Extract user content from messages
        user_content = ""
        for msg in request.messages:
            if msg.role == "user":
                user_content = msg.content
                break

        if not user_content:
            raise HTTPException(status_code=400, detail="No user content provided")

        # Create critique config
        config = CritiqueConfigSchema(
            content=user_content,
            task_type=TaskType.CODE_REVIEW,  # Default for now
        )

        # Run the full debate engine
        engine = get_quick_engine()
        consensus = await _maybe_await(engine.critique, config)

        # Convert to dict for JSON response
        result = {
            "final_conclusion": consensus.final_conclusion,
            "consensus_confidence": consensus.consensus_confidence,
            "critiques_summary": [
                {
                    "role_id": c.role_id,
                    "severity": c.severity.value,
                    "target_area": c.target_area,
                    "defect_type": c.defect_type,
                    "evidence": c.evidence,
                    "suggested_fix": c.suggested_fix,
                    "confidence": c.confidence,
                    "is_devil_advocate": getattr(c, "is_devil_advocate", False),
                }
                for c in consensus.critiques_summary
            ],
            "debate_metadata": {
                "request_id": consensus.debate_metadata.request_id,
                "task_type": consensus.debate_metadata.task_type.value,
                "provider_mode": consensus.debate_metadata.provider_mode.value,
                "rounds_completed": consensus.debate_metadata.rounds_completed,
                "total_cost_usd": consensus.debate_metadata.total_cost_usd,
                "total_latency_ms": consensus.debate_metadata.total_latency_ms,
                "models_used": consensus.debate_metadata.models_used,
                "quorum_achieved": consensus.debate_metadata.quorum_achieved,
                "termination_reason": consensus.debate_metadata.termination_reason.value,
                "parse_attempts_total": consensus.debate_metadata.parse_attempts_total,
            },
            "adopted_contributions": consensus.adopted_contributions,
            "rejected_positions": consensus.rejected_positions,
            "remaining_disagreements": consensus.remaining_disagreements,
            "disagreement_confirmation": consensus.disagreement_confirmation,
            "preserved_minority_opinions": consensus.preserved_minority_opinions,
            "partial_return": consensus.partial_return,
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quick-critique")
async def quick_critique_api(request: CritiqueRequest):
    """Quick critique endpoint using DebateEngine."""
    try:
        # Create critique config
        task_type_str = request.task_type
        if task_type_str != "AUTO":
            try:
                task_type_val: TaskType = TaskType(task_type_str)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid task_type: {task_type_str}")
        else:
            task_type_val = TaskType.AUTO

        config = CritiqueConfigSchema(content=request.content, task_type=task_type_val)

        # Run the full debate engine
        engine = get_quick_engine()
        consensus = await _maybe_await(engine.critique, config)

        # Convert to dict for JSON response
        result = {
            "final_conclusion": consensus.final_conclusion,
            "consensus_confidence": consensus.consensus_confidence,
            "critiques_summary": [
                {
                    "role_id": c.role_id,
                    "severity": c.severity.value,
                    "target_area": c.target_area,
                    "defect_type": c.defect_type,
                    "evidence": c.evidence,
                    "suggested_fix": c.suggested_fix,
                    "confidence": c.confidence,
                    "is_devil_advocate": getattr(c, "is_devil_advocate", False),
                }
                for c in consensus.critiques_summary
            ],
            "debate_metadata": {
                "request_id": consensus.debate_metadata.request_id,
                "task_type": consensus.debate_metadata.task_type.value,
                "provider_mode": consensus.debate_metadata.provider_mode.value,
                "rounds_completed": consensus.debate_metadata.rounds_completed,
                "total_cost_usd": consensus.debate_metadata.total_cost_usd,
                "total_latency_ms": consensus.debate_metadata.total_latency_ms,
                "models_used": consensus.debate_metadata.models_used,
                "quorum_achieved": consensus.debate_metadata.quorum_achieved,
                "termination_reason": consensus.debate_metadata.termination_reason.value,
                "parse_attempts_total": consensus.debate_metadata.parse_attempts_total,
            },
            "adopted_contributions": consensus.adopted_contributions,
            "rejected_positions": consensus.rejected_positions,
            "remaining_disagreements": consensus.remaining_disagreements,
            "disagreement_confirmation": consensus.disagreement_confirmation,
            "preserved_minority_opinions": consensus.preserved_minority_opinions,
            "partial_return": consensus.partial_return,
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_api_key(request: Request) -> None:
    """Validate API key for accessing protected endpoints.

    Raises HTTPException 401 if API key is missing or invalid.
    Only validates when DEBATE_ENGINE_API_KEYS is explicitly set.
    """
    # Get configured API keys from environment
    allowed_api_keys = os.getenv("DEBATE_ENGINE_API_KEYS", "").split(",")
    allowed_api_keys = [key.strip() for key in allowed_api_keys if key.strip()]

    # Get API key from header
    api_key = request.headers.get("X-API-Key")

    # Only validate API key if DEBATE_ENGINE_API_KEYS is explicitly set
    if allowed_api_keys:
        # If API keys are configured, require a valid one
        if not api_key or api_key not in allowed_api_keys:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
