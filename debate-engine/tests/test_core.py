import pytest
from debate_engine.schemas import (
    CritiqueSchema,
    ConsensusSchema,
    CritiqueConfigSchema,
    TaskType,
    Severity,
    DefectType,
    FixKind,
)
from debate_engine.orchestration import QuickCritiqueEngine


@pytest.mark.asyncio
async def test_critique_schema_validation():
    """测试批评 Schema 验证"""
    # 有效的批评
    valid_critique = {
        "target_area": "数据库查询",
        "defect_type": "PERFORMANCE_ISSUE",
        "severity": "CRITICAL",
        "evidence": "查询语句未使用索引，导致查询时间过长",
        "suggested_fix": "添加索引，优化查询语句",
        "fix_kind": "CONCRETE_FIX",
        "confidence": 0.9,
    }
    critique = CritiqueSchema(**valid_critique)
    assert critique.target_area == "数据库查询"
    assert critique.defect_type == DefectType.PERFORMANCE_ISSUE
    assert critique.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_critique_config_schema_validation():
    """测试批评配置 Schema 验证"""
    # 有效的配置
    valid_config = {
        "content": "def vulnerable_function(user_input):\n    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n    return execute_query(query)",
        "task_type": "CODE_REVIEW",
    }
    config = CritiqueConfigSchema(**valid_config)
    assert config.content is not None
    assert config.task_type == "CODE_REVIEW"


@pytest.mark.asyncio
async def test_quick_critique_engine():
    """测试快速批评引擎"""
    engine = QuickCritiqueEngine()
    config = CritiqueConfigSchema(
        content="def vulnerable_function(user_input):\n    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n    return execute_query(query)",
        task_type=TaskType.CODE_REVIEW,
    )
    
    # 运行批评
    consensus = await engine.critique(config)
    
    # 验证结果
    assert isinstance(consensus, ConsensusSchema)
    assert consensus.total_critiques >= 2
    assert consensus.final_conclusion is not None
    assert consensus.execution_time > 0
