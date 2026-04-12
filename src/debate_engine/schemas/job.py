"""Job tracking schema for async DebateEngine execution."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from .consensus import ConsensusSchema
from .enums import JobStatus


class ErrorDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message: str = Field(...)
    code: str = Field(...)


class DebateJobSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    job_id: str = Field(...)
    status: JobStatus = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    current_round: int = Field(default=0, ge=0)
    current_phase: str = Field(default="")
    progress_pct: int = Field(default=0, ge=0, le=100)
    result: Optional[ConsensusSchema] = None
    error: Optional[ErrorDetail] = None
    cost_so_far_usd: float = Field(default=0.0, ge=0.0)