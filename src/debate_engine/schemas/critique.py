"""CritiqueSchema -- the core machine-parseable critique unit."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from .enums import DefectType, FixKind, Severity


class CritiqueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_area: str = Field(..., min_length=10, max_length=200,
        description="The specific section or aspect being critiqued.")
    defect_type: DefectType = Field(..., description="Classification of the identified defect.")
    severity: Severity = Field(..., description="Severity level (CRITICAL, MAJOR, or MINOR).")
    evidence: str = Field(..., min_length=20, description="Supporting evidence for the critique.")
    suggested_fix: str = Field(..., min_length=20, description="Actionable recommendation.")
    fix_kind: FixKind = Field(..., description="Nature of the suggested fix.")
    is_devil_advocate: bool = Field(default=False,
        description="Whether this critique was produced by the devil's advocate role.")
    confidence: float = Field(..., ge=0.0, le=1.0,
        description="Reviewer confidence (0.0-1.0).")
    role_id: Optional[str] = Field(default=None,
        description="Identifier of the role (system-managed).")
    raw_response: Optional[str] = Field(default=None,
        description="Original LLM response for parse-repair fallback.")