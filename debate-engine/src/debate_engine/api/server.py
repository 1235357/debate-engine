from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..schemas import (
    CritiqueConfigSchema,
    ConsensusSchema,
    TaskType,
)
from ..orchestration import QuickCritiqueEngine

app = FastAPI(
    title="DebateEngine API",
    description="结构化多智能体对抗批评引擎 API",
    version="0.2.0",
)

engine = QuickCritiqueEngine()


class CritiqueRequest(BaseModel):
    """批评请求"""
    content: str
    task_type: str
    max_rounds: Optional[int] = 2
    provider_mode: Optional[str] = "stable"


@app.post("/v1/quick-critique", response_model=ConsensusSchema)
async def quick_critique(request: CritiqueRequest):
    """快速批评"""
    try:
        config = CritiqueConfigSchema(
            content=request.content,
            task_type=request.task_type,
            max_rounds=request.max_rounds,
            provider_mode=request.provider_mode,
        )
        consensus = await engine.critique(config)
        return consensus
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
