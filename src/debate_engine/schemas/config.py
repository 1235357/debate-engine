"""Configuration schemas for DebateEngine."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import ConvergenceMode, ProviderMode, TaskType


class CritiqueConfigSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    content: str = Field(..., min_length=10, max_length=8000)
    task_type: TaskType = Field(default=TaskType.AUTO)
    provider_mode: ProviderMode = Field(default=ProviderMode.STABLE)
    enable_devil_advocate: bool = Field(default=True)
    cost_budget_usd: float = Field(default=0.30, gt=0.0)
    custom_role_prompts: dict[str, str] | None = None
    model: str | None = None


class DebateConfigSchema(CritiqueConfigSchema):
    model_config = ConfigDict(from_attributes=True)
    max_rounds: int = Field(default=2, ge=1, le=2)
    convergence_mode: ConvergenceMode = Field(default=ConvergenceMode.CRITICAL_CLEARED)
    revision_instructions: str | None = None
