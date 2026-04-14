"""ConsensusSchema -- the final output of a DebateEngine run."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .critique import CritiqueSchema
from .enums import ProviderMode, Severity, TaskType, TerminationReason


class RejectedPosition(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    claim: str = Field(..., description="The rejected position.")
    rejection_reason: str = Field(..., description="Why it was rejected.")


class MinorityOpinion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    opinion: str = Field(..., description="The dissenting opinion.")
    source_role: str = Field(..., description="Which role held this opinion.")
    source_critique_severity: Severity = Field(
        ..., description="Severity of the original critique."
    )
    potential_risk_if_ignored: str = Field(..., description="Risk if this opinion is ignored.")


class DebateMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str | None = None
    task_type: TaskType = Field(...)
    provider_mode: ProviderMode = Field(...)
    rounds_completed: int = Field(default=1, ge=1)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_latency_ms: float = Field(default=0.0, ge=0.0)
    models_used: list[str] = Field(default_factory=list)
    quorum_achieved: bool = Field(...)
    termination_reason: TerminationReason = Field(...)
    parse_attempts_total: int = Field(default=0, ge=0)


class ConsensusSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    final_conclusion: str = Field(..., description="The judge's final conclusion.")
    consensus_confidence: float = Field(..., ge=0.0, le=0.95)
    adopted_contributions: dict[str, list[str]] = Field(default_factory=dict)
    rejected_positions: list[RejectedPosition] = Field(default_factory=list)
    remaining_disagreements: list[str] = Field(default_factory=list)
    disagreement_confirmation: str | None = None
    preserved_minority_opinions: list[MinorityOpinion] = Field(default_factory=list)
    partial_return: bool = Field(default=False)
    critiques_summary: list[CritiqueSchema] = Field(default_factory=list)
    debate_metadata: DebateMetadata = Field(...)

    @model_validator(mode="after")
    def _validate_consistency(self) -> ConsensusSchema:
        if len(self.remaining_disagreements) == 0 and not self.disagreement_confirmation:
            raise ValueError(
                "disagreement_confirmation is required when remaining_disagreements is empty."
            )
        if self.partial_return and len(self.critiques_summary) == 0:
            raise ValueError("critiques_summary must be non-empty when partial_return is True.")
        if self.consensus_confidence > 0.95:
            raise ValueError("consensus_confidence must not exceed 0.95.")
        return self
