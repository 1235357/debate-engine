#!/usr/bin/env python3
"""API server for DebateEngine using NVIDIA API with multi-key support."""

import os
import threading
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import DebateEngine components
from debate_engine.orchestration.quick_critique import QuickCritiqueEngine
from debate_engine.schemas import CritiqueConfigSchema, TaskType

app = FastAPI(
    title="DebateEngine API",
    description="Structured Multi-Agent Critique & Consensus Engine",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class APIKeyManager:
    """Manage multiple API keys with load balancing and failover."""

    def __init__(self, api_keys: list[str], base_url: str, model: str):
        self.api_keys = api_keys
        self.base_url = base_url
        self.model = model
        self.current_index = 0
        self.lock = threading.Lock()
        self.key_stats: dict[str, dict] = defaultdict(
            lambda: {
                "success_count": 0,
                "failure_count": 0,
                "last_used": 0,
                "last_failed": 0,
                "is_active": True,
            }
        )
        self.cooldown_period = 60

    def get_next_key(self) -> str:
        """Get next API key using round-robin with failover."""
        with self.lock:
            start_index = self.current_index
            attempt = 0

            while attempt < len(self.api_keys):
                key = self.api_keys[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.api_keys)

                stats = self.key_stats[key]
                now = time.time()

                if stats["is_active"]:
                    if now - stats["last_failed"] > self.cooldown_period:
                        return key

                attempt += 1

            self.current_index = start_index
            return self.api_keys[start_index]

    def record_success(self, api_key: str):
        """Record a successful API call."""
        with self.lock:
            stats = self.key_stats[api_key]
            stats["success_count"] += 1
            stats["last_used"] = time.time()
            stats["is_active"] = True

    def record_failure(self, api_key: str):
        """Record a failed API call."""
        with self.lock:
            stats = self.key_stats[api_key]
            stats["failure_count"] += 1
            stats["last_failed"] = time.time()
            stats["is_active"] = False

    def get_stats(self) -> dict:
        """Get statistics about API key usage."""
        with self.lock:
            return {
                "total_keys": len(self.api_keys),
                "active_keys": sum(1 for k in self.api_keys if self.key_stats[k]["is_active"]),
                "key_details": {
                    f"key_{i}": {
                        "success_count": self.key_stats[k]["success_count"],
                        "failure_count": self.key_stats[k]["failure_count"],
                        "is_active": self.key_stats[k]["is_active"],
                    }
                    for i, k in enumerate(self.api_keys)
                },
            }


def load_api_keys() -> list[str]:
    """Load API keys from environment variables."""
    keys = []

    primary_key = os.getenv("NVIDIA_API_KEY")
    if primary_key:
        keys.append(primary_key)

    for i in range(1, 11):
        key = os.getenv(f"NVIDIA_API_KEY_{i}")
        if key:
            keys.append(key)

    return keys


BASE_URL = os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "minimaxai/minimax-m2.7")

try:
    API_KEYS = load_api_keys()
    if API_KEYS:
        key_manager = APIKeyManager(API_KEYS, BASE_URL, DEFAULT_MODEL)
        # Initialize DebateEngine with NVIDIA API keys
        os.environ["NVIDIA_API_KEY"] = API_KEYS[0]
        for i, key in enumerate(API_KEYS[1:], 1):
            os.environ[f"NVIDIA_API_KEY_{i}"] = key
        # Set provider mode to use NVIDIA
        os.environ["DEBATE_ENGINE_PROVIDER_MODE"] = "diverse"
        # Initialize the engine with key manager
        engine = QuickCritiqueEngine(key_manager=key_manager)
    else:
        print("Warning: No NVIDIA API keys found. Engine will not be initialized.")
        key_manager = None
        engine = None
except Exception as e:
    print(f"Warning: {e}")
    key_manager = None
    engine = None


class CritiqueRequest(BaseModel):
    content: str
    task_type: str = "CODE_REVIEW"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = DEFAULT_MODEL


class StreamResponse(BaseModel):
    content: str
    finish_reason: str | None = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = key_manager.get_stats() if key_manager else {}
    return {"status": "healthy", "model": DEFAULT_MODEL, "api_keys": stats}


@app.get("/api/stats")
async def get_stats():
    """Get API key usage statistics."""
    if not key_manager:
        raise HTTPException(status_code=500, detail="API key manager not initialized")
    return key_manager.get_stats()


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint using DebateEngine with full multi-agent transparency."""
    try:
        if not engine:
            raise HTTPException(status_code=503, detail="DebateEngine not initialized. Please check API key configuration.")
        
        # Extract user content from messages
        user_content = ""
        for msg in request.messages:
            if msg.role == "user":
                user_content = msg.content
                break

        if not user_content:
            raise HTTPException(status_code=400, detail="No user content provided")

        # Create critique config with AUTO task type for automatic detection
        config = CritiqueConfigSchema(
            content=user_content,
            task_type="AUTO",  # Let the engine detect task type automatically
        )

        # Run the full debate engine
        consensus = await engine.critique(config)

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
async def quick_critique(request: CritiqueRequest):
    """Quick critique endpoint using DebateEngine."""
    try:
        # Create critique config
        config = CritiqueConfigSchema(
            content=request.content,
            task_type=TaskType(request.task_type) if request.task_type != "AUTO" else "AUTO",
        )

        # Run the full debate engine
        consensus = await engine.critique(config)

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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
