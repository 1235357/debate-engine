"""DebateEngine Schema Package.

Re-exports all schema classes for convenient access via
``from debate_engine.schemas import ...``.
"""

from .config import CritiqueConfigSchema, DebateConfigSchema
from .consensus import (
    ConsensusSchema,
    DebateMetadata,
    MinorityOpinion,
    RejectedPosition,
)
from .critique import CritiqueSchema
from .enums import (
    ConvergenceMode,
    DefectType,
    FixKind,
    JobStatus,
    ProviderMode,
    RoleStatus,
    Severity,
    TaskType,
    TerminationReason,
)
from .job import DebateJobSchema, ErrorDetail
from .proposal import ProposalSchema, RevisionSchema

__all__ = [
    "CritiqueConfigSchema",
    "DebateConfigSchema",
    "ConsensusSchema",
    "DebateMetadata",
    "MinorityOpinion",
    "RejectedPosition",
    "CritiqueSchema",
    "ConvergenceMode",
    "DefectType",
    "FixKind",
    "JobStatus",
    "ProviderMode",
    "RoleStatus",
    "Severity",
    "TaskType",
    "TerminationReason",
    "DebateJobSchema",
    "ErrorDetail",
    "ProposalSchema",
    "RevisionSchema",
]