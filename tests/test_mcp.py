"""MCP server tests for DebateEngine."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from debate_engine.mcp_server.server import (  
    format_consensus_as_markdown, 
    format_eval_scores_as_markdown,
    _parse_consensus_json
)


def test_format_consensus_as_markdown():
    """Test formatting consensus as markdown."""
    # Create a mock consensus object
    mock_consensus = Mock(
        partial_return=False,
        final_conclusion="Test conclusion",
        consensus_confidence=0.85,
        debate_metadata=Mock(
            request_id="test-request-id",
            job_id="test-job-id",
            task_type=Mock(value="CODE_REVIEW"),
            provider_mode=Mock(value="STABLE"),
            rounds_completed=2,
            quorum_achieved=True,
            total_cost_usd=0.1,
            total_latency_ms=2000.0,
            models_used=["test-model-1", "test-model-2"],
            termination_reason=Mock(value="COMPLETED")
        ),
        critiques_summary=[
            Mock(
                severity=Mock(value="MAJOR"),
                role_id="ROLE_A",
                target_area="Code quality",
                defect_type=Mock(value="Performance issue"),
                evidence="Loop could be optimized",
                suggested_fix="Use list comprehension",
                fix_kind=Mock(value="REFACTOR"),
                is_devil_advocate=False,
                confidence=0.9
            )
        ],
        adopted_contributions={
            "ROLE_A": ["Suggested optimization"]
        },
        rejected_positions=[
            Mock(
                claim="No issues found",
                rejection_reason="Evidence provided for performance issue"
            )
        ],
        remaining_disagreements=["Minor implementation details"],
        preserved_minority_opinions=[
            Mock(
                opinion="Alternative approach suggested",
                source_role="ROLE_B",
                source_critique_severity=Mock(value="MINOR"),
                potential_risk_if_ignored="May not scale well"
            )
        ]
    )

    # Test the formatting function
    markdown = format_consensus_as_markdown(mock_consensus)
    
    assert "# DebateEngine Consensus" in markdown
    assert "Test conclusion" in markdown
    assert "**Confidence:** 85%" in markdown
    assert "## Metadata" in markdown
    assert "test-request-id" in markdown
    assert "## Findings" in markdown
    assert "MAJOR" in markdown
    assert "Code quality" in markdown
    assert "## Adopted Contributions" in markdown
    assert "Suggested optimization" in markdown
    assert "## Rejected Positions" in markdown
    assert "No issues found" in markdown
    assert "## Remaining Disagreements" in markdown
    assert "Minor implementation details" in markdown
    assert "## Minority Opinions (Preserved)" in markdown
    assert "Alternative approach suggested" in markdown


def test_format_eval_scores_as_markdown():
    """Test formatting evaluation scores as markdown."""
    # Test data
    scores = {
        "BDR": 0.8,
        "FAR": 0.1,
        "CV": 0.9,
        "CIS": 0.7,
        "CE": 0.85,
        "RD": 0.9,
        "HD": 0.15
    }

    # Test the formatting function
    markdown = format_eval_scores_as_markdown(scores)
    
    assert "# DebateEval Scores" in markdown
    assert "BDR" in markdown
    assert "FAR" in markdown
    assert "CV" in markdown
    assert "CIS" in markdown
    assert "CE" in markdown
    assert "RD" in markdown
    assert "HD" in markdown
    assert "Average Score" in markdown


def test_parse_consensus_json():
    """Test parsing consensus JSON."""
    # Test JSON data
    consensus_json = json.dumps({
        "final_conclusion": "Test conclusion",
        "consensus_confidence": 0.85,
        "critiques_summary": [],
        "debate_metadata": {
            "request_id": "test-request-id",
            "task_type": "CODE_REVIEW",
            "provider_mode": "STABLE",
            "rounds_completed": 1,
            "total_cost_usd": 0.05,
            "total_latency_ms": 1000.0,
            "models_used": ["test-model"],
            "quorum_achieved": True,
            "termination_reason": "COMPLETED",
            "parse_attempts_total": 0
        },
        "adopted_contributions": {},
        "rejected_positions": [],
        "remaining_disagreements": [],
        "disagreement_confirmation": "",
        "preserved_minority_opinions": [],
        "partial_return": False
    })

    # Test the parsing function
    with patch("debate_engine.schemas.ConsensusSchema") as mock_schema:
        mock_schema.model_validate.return_value = Mock()
        result = _parse_consensus_json(consensus_json)
        mock_schema.model_validate.assert_called_once()
        assert result is not None
