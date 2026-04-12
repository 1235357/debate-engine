from enum import Enum


class TaskType(str, Enum):
    """任务类型"""
    CODE_REVIEW = "CODE_REVIEW"
    RAG_VALIDATION = "RAG_VALIDATION"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    ARTICLE_CRITIQUE = "ARTICLE_CRITIQUE"


class DefectType(str, Enum):
    """缺陷类型"""
    SECURITY_VULNERABILITY = "SECURITY_VULNERABILITY"
    PERFORMANCE_ISSUE = "PERFORMANCE_ISSUE"
    LOGIC_ERROR = "LOGIC_ERROR"
    CODE_STYLE = "CODE_STYLE"
    DOCUMENTATION_ISSUE = "DOCUMENTATION_ISSUE"
    FACTUAL_ERROR = "FACTUAL_ERROR"
    ARCHITECTURE_FLAW = "ARCHITECTURE_FLAW"
    OTHER = "OTHER"


class Severity(str, Enum):
    """严重程度"""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class FixKind(str, Enum):
    """修复类型"""
    CONCRETE_FIX = "CONCRETE_FIX"
    SUGGESTION = "SUGGESTION"
    REFACTOR = "REFACTOR"


class ProviderMode(str, Enum):
    """供应商模式"""
    STABLE = "stable"
    BALANCED = "balanced"
    DIVERSE = "diverse"


class RoleType(str, Enum):
    """角色类型"""
    ROLE_A = "ROLE_A"
    ROLE_B = "ROLE_B"
    DA_ROLE = "DA_ROLE"
    JUDGE = "JUDGE"
