"""Proposal and revision schemas for multi-round debate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProposalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role_id: str = Field(...)
    core_claim: str = Field(...)
    supporting_arguments: list[str] = Field(default_factory=list)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    is_devil_advocate: bool = Field(default=False)


class RevisionSchema(ProposalSchema):
    model_config = ConfigDict(from_attributes=True)
    changes_from_previous: str = Field(...)
