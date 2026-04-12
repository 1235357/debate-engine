from pydantic import BaseModel, Field, field_validator
from typing import Optional
from .enums import DefectType, Severity, FixKind, RoleType


class CritiqueSchema(BaseModel):
    """批评 Schema"""
    target_area: str = Field(..., description="批评的目标区域")
    defect_type: DefectType = Field(..., description="缺陷类型")
    severity: Severity = Field(..., description="严重程度")
    evidence: str = Field(..., min_length=10, description="证据")
    suggested_fix: str = Field(..., min_length=5, description="建议的修复方案")
    fix_kind: FixKind = Field(..., description="修复类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    is_devil_advocate: bool = Field(default=False, description="是否为魔鬼代言人")
    role_type: Optional[RoleType] = Field(default=None, description="角色类型")

    @field_validator('evidence')
    @classmethod
    def validate_evidence(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('证据长度至少为 10 个字符')
        return v

    @field_validator('suggested_fix')
    @classmethod
    def validate_suggested_fix(cls, v):
        if len(v.strip()) < 5:
            raise ValueError('建议的修复方案长度至少为 5 个字符')
        return v


class CritiqueConfigSchema(BaseModel):
    """批评配置 Schema"""
    content: str = Field(..., min_length=10, description="待批评的内容")
    task_type: str = Field(..., description="任务类型")
    max_rounds: Optional[int] = Field(default=2, ge=1, le=5, description="最大轮数")
    provider_mode: Optional[str] = Field(default="stable", description="供应商模式")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('待批评的内容长度至少为 10 个字符')
        return v
