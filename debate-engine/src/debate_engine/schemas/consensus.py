from pydantic import BaseModel, Field
from typing import List, Optional
from .critique import CritiqueSchema
from .enums import Severity


class MinorityOpinionSchema(BaseModel):
    """少数意见 Schema"""
    opinion: str = Field(..., description="少数意见内容")
    source_critique_severity: Severity = Field(..., description="来源批评的严重程度")
    potential_risk_if_ignored: str = Field(..., description="如果忽略的潜在风险")


class ConsensusSchema(BaseModel):
    """共识 Schema"""
    final_conclusion: str = Field(..., description="最终结论")
    consensus_confidence: float = Field(..., ge=0.0, le=1.0, description="共识置信度")
    critiques_summary: List[CritiqueSchema] = Field(..., description="批评摘要")
    remaining_disagreements: List[str] = Field(default_factory=list, description="剩余分歧")
    preserved_minority_opinions: List[MinorityOpinionSchema] = Field(default_factory=list, description="保留的少数意见")
    total_critiques: int = Field(..., description="总批评数")
    critical_critiques: int = Field(..., description="严重批评数")
    major_critiques: int = Field(..., description="主要批评数")
    minor_critiques: int = Field(..., description="次要批评数")
    execution_time: float = Field(..., description="执行时间（秒）")
    conformity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="从众分数")
