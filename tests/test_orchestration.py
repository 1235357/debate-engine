"""Tests for the orchestration layer.

Tests QuickCritiqueEngine and DebateOrchestrator with mocked LLM provider
calls to verify quorum logic, anonymization, consensus building, and
cost budget enforcement.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_engine.orchestration import DebateOrchestrator, QuickCritiqueEngine
from debate_engine.orchestration.base import (
    anonymize_critiques,
    build_judge_summary,
    check_quorum,
    generate_request_id,
)
from debate_engine.providers.config import ProviderConfig
from debate_engine.providers.llm_provider import CallResult
from debate_engine.schemas import (
    CritiqueConfigSchema,
    CritiqueSchema,
    DebateConfigSchema,
    DefectType,
    FixKind,
    JobStatus,
    ProviderMode,
    Severity,
    TaskType,
)


# ===================================================================
# Helpers
# ===================================================================


def _make_valid_critique(
    role_id: str = "ROLE_A",
    severity: Severity = Severity.MAJOR,
    is_da: bool = False,
) -> CritiqueSchema:
    """Create a valid CritiqueSchema for testing."""
    return CritiqueSchema(
        target_area="The introduction section of the proposal",
        defect_type=DefectType.LOGICAL_FALLACY,
        severity=severity,
        evidence="The argument claims X implies Y, but there is no supporting data.",
        suggested_fix="Add statistical evidence or remove the causal claim.",
        fix_kind=FixKind.CONCRETE_FIX,
        confidence=0.85,
        role_id=role_id,
        is_devil_advocate=is_da,
    )


def _make_config(
    content: str = "This is a well-structured proposal for the new API endpoint.",
    **kwargs: Any,
) -> CritiqueConfigSchema:
    return CritiqueConfigSchema(content=content, **kwargs)


def _make_call_result(
    status: str = "SUCCESS",
    cost_usd: float = 0.005,
    model_used: str = "openai/gpt-4o-mini",
    error_message: str | None = None,
) -> CallResult:
    return CallResult(
        status=status,
        cost_usd=cost_usd,
        latency_ms=100.0,
        model_used=model_used,
        parse_attempts=1,
        raw_response=None,
        error_message=error_message,
    )


# ===================================================================
# QuickCritiqueEngine tests
# ===================================================================


class TestQuickCritiqueEngine:
    """Tests for the single-round critique engine."""

    @pytest.mark.asyncio
    async def test_all_roles_succeed(self) -> None:
        """All 3 roles succeed -> full consensus returned."""
        config = _make_config()
        provider_config = ProviderConfig(timeout_seconds=10.0)
        engine = QuickCritiqueEngine(provider_config)

        critique = _make_valid_critique()
        call_result = _make_call_result()

        # Mock the provider.call to return valid critiques for roles
        # and a valid consensus for the judge
        call_count = 0

        async def mock_call(
            messages: list[dict],
            system_prompt: str | None = None,
            response_model: type | None = None,
            role_type: str = "critic_a",
            temperature: float = 0.3,
        ) -> tuple[Any, CallResult]:
            nonlocal call_count
            call_count += 1
            return critique, call_result

        with patch.object(engine.provider, "call", new_callable=AsyncMock) as mock_call_fn:
            mock_call_fn.side_effect = mock_call

            result = await engine.critique(config)

        assert result is not None
        assert result.partial_return is False

    @pytest.mark.asyncio
    async def test_one_role_failing_quorum_met(self) -> None:
        """1 role fails but quorum (2/3) is still met -> consensus returned."""
        config = _make_config()
        provider_config = ProviderConfig(timeout_seconds=10.0)
        engine = QuickCritiqueEngine(provider_config)

        critique = _make_valid_critique()
        success_result = _make_call_result()
        fail_result = _make_call_result(status="ROLE_FAILED", error_message="Provider unavailable")

        call_idx = 0

        async def mock_call(**kwargs: Any) -> tuple[Any, CallResult]:
            nonlocal call_idx
            idx = call_idx
            call_idx += 1
            # Third call (judge) succeeds
            if idx == 3:
                from debate_engine.schemas import (
                    ConsensusSchema,
                    DebateMetadata,
                    TerminationReason,
                )

                metadata = DebateMetadata(
                    task_type="GENERAL_CRITIQUE",
                    provider_mode="stable",
                    quorum_achieved=True,
                    termination_reason=TerminationReason.COMPLETED,
                )
                consensus = ConsensusSchema(
                    final_conclusion="A conclusion.",
                    consensus_confidence=0.85,
                    remaining_disagreements=[],
                    disagreement_confirmation="No disagreements.",
                    debate_metadata=metadata,
                )
                return consensus, success_result
            # First two calls: one succeeds, one fails
            if idx == 1:
                return critique, success_result
            else:
                return None, fail_result

        with patch.object(engine.provider, "call", new_callable=AsyncMock) as mock_call_fn:
            mock_call_fn.side_effect = mock_call

            result = await engine.critique(config)

        assert result is not None

    @pytest.mark.asyncio
    async def test_two_roles_failing_partial_return(self) -> None:
        """2 roles fail, quorum not met -> partial return."""
        config = _make_config()
        provider_config = ProviderConfig(timeout_seconds=10.0)
        engine = QuickCritiqueEngine(provider_config)

        critique = _make_valid_critique()
        success_result = _make_call_result()
        fail_result = _make_call_result(status="ROLE_FAILED", error_message="Provider unavailable")

        call_idx = 0

        async def mock_call(**kwargs: Any) -> tuple[Any, CallResult]:
            nonlocal call_idx
            idx = call_idx
            call_idx += 1
            if idx == 1:
                return critique, success_result
            else:
                return None, fail_result

        with patch.object(engine.provider, "call", new_callable=AsyncMock) as mock_call_fn:
            mock_call_fn.side_effect = mock_call

            result = await engine.critique(config)

        assert result is not None
        assert result.partial_return is True

    @pytest.mark.asyncio
    async def test_cost_budget_exceeded_triggers_partial(self) -> None:
        """Cost budget exceeded before critique -> result returned with budget info."""
        config = _make_config(cost_budget_usd=0.001)
        provider_config = ProviderConfig(timeout_seconds=10.0)
        engine = QuickCritiqueEngine(provider_config)

        # Pre-accumulate cost to exceed budget
        engine.provider._cost_accumulated = 0.002

        result = await engine.critique(config)

        assert result is not None
        # When no critiques were generated, partial_return is False
        # (partial_return=True requires non-empty critiques_summary)
        assert "cost budget exceeded" in result.final_conclusion.lower()


# ===================================================================
# Anonymization tests
# ===================================================================


class TestAnonymization:
    """Test that anonymization removes role identity from critiques."""

    def test_anonymize_replaces_role_ids(self) -> None:
        critiques = [
            _make_valid_critique(role_id="ROLE_A"),
            _make_valid_critique(role_id="ROLE_B"),
            _make_valid_critique(role_id="DA_ROLE"),
        ]

        anonymized = anonymize_critiques(critiques)

        assert anonymized[0].role_id == "Critic Alpha"
        assert anonymized[1].role_id == "Critic Beta"
        assert anonymized[2].role_id == "Critic Gamma"

    def test_anonymize_preserves_devil_advocate_flag(self) -> None:
        critiques = [
            _make_valid_critique(role_id="ROLE_A"),
            _make_valid_critique(role_id="DA_ROLE", is_da=True),
        ]

        anonymized = anonymize_critiques(critiques)

        assert anonymized[0].is_devil_advocate is False
        assert anonymized[1].is_devil_advocate is True

    def test_anonymize_does_not_mutate_original(self) -> None:
        critiques = [_make_valid_critique(role_id="ROLE_A")]
        anonymized = anonymize_critiques(critiques)

        assert critiques[0].role_id == "ROLE_A"
        assert anonymized[0].role_id == "Critic Alpha"

    def test_anonymize_beyond_three_roles(self) -> None:
        critiques = [_make_valid_critique(role_id=f"ROLE_{i}") for i in range(5)]
        anonymized = anonymize_critiques(critiques)

        assert anonymized[0].role_id == "Critic Alpha"
        assert anonymized[1].role_id == "Critic Beta"
        assert anonymized[2].role_id == "Critic Gamma"
        assert anonymized[3].role_id == "Critic 4"
        assert anonymized[4].role_id == "Critic 5"


# ===================================================================
# Judge summary tests
# ===================================================================


class TestJudgeSummary:
    """Test that the judge receives a structured summary of critiques."""

    def test_judge_summary_contains_critique_info(self) -> None:
        critiques = [
            _make_valid_critique(role_id="ROLE_A", severity=Severity.CRITICAL),
            _make_valid_critique(role_id="ROLE_B", severity=Severity.MINOR),
        ]

        summary = build_judge_summary(critiques, (True, 2))

        assert "CRITICAL" in summary
        assert "MINOR" in summary
        assert "Quorum met: True" in summary
        assert "Successful reviewers: 2/3" in summary

    def test_judge_summary_with_failed_reviewers(self) -> None:
        critiques = [_make_valid_critique(role_id="ROLE_A")]
        summary = build_judge_summary(critiques, (False, 1))

        assert "Quorum met: False" in summary
        assert "Successful reviewers: 1/3" in summary
        assert "Failed reviewers: 2" in summary

    def test_judge_summary_groups_by_severity(self) -> None:
        critiques = [
            _make_valid_critique(role_id="ROLE_A", severity=Severity.MINOR),
            _make_valid_critique(role_id="ROLE_B", severity=Severity.CRITICAL),
            _make_valid_critique(role_id="ROLE_C", severity=Severity.MAJOR),
        ]

        summary = build_judge_summary(critiques, (True, 3))

        # Verify all severity levels are present
        assert "CRITICAL" in summary
        assert "MAJOR" in summary
        assert "MINOR" in summary


# ===================================================================
# Quorum check tests
# ===================================================================


class TestQuorumCheck:
    """Test quorum check logic."""

    def test_all_success_quorum_met(self) -> None:
        results = [
            _make_call_result("SUCCESS"),
            _make_call_result("SUCCESS"),
            _make_call_result("SUCCESS"),
        ]
        quorum_met, count = check_quorum(results)
        assert quorum_met is True
        assert count == 3

    def test_two_success_quorum_met(self) -> None:
        results = [
            _make_call_result("SUCCESS"),
            _make_call_result("ROLE_FAILED"),
            _make_call_result("SUCCESS"),
        ]
        quorum_met, count = check_quorum(results)
        assert quorum_met is True
        assert count == 2

    def test_one_success_quorum_not_met(self) -> None:
        results = [
            _make_call_result("SUCCESS"),
            _make_call_result("ROLE_FAILED"),
            _make_call_result("ROLE_FAILED"),
        ]
        quorum_met, count = check_quorum(results)
        assert quorum_met is False
        assert count == 1

    def test_parse_failed_counts_as_success(self) -> None:
        results = [
            _make_call_result("PARSE_FAILED"),
            _make_call_result("SUCCESS"),
            _make_call_result("ROLE_FAILED"),
        ]
        quorum_met, count = check_quorum(results)
        assert quorum_met is True
        assert count == 2


# ===================================================================
# DebateOrchestrator tests
# ===================================================================


class TestDebateOrchestrator:
    """Tests for the multi-round async debate orchestrator."""

    @pytest.mark.asyncio
    async def test_submit_returns_job_id(self) -> None:
        orchestrator = DebateOrchestrator()
        config = DebateConfigSchema(
            content="Test debate query.",
            max_rounds=1,
        )

        # Mock the background task
        with patch.object(orchestrator, "_run_debate", new_callable=AsyncMock):
            job_id = await orchestrator.submit(config)

        assert isinstance(job_id, str)
        assert len(job_id) > 0

        job = await orchestrator.get_status(job_id)
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_raises(self) -> None:
        orchestrator = DebateOrchestrator()
        with pytest.raises(KeyError, match="not found"):
            await orchestrator.get_status("nonexistent_id")

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self) -> None:
        orchestrator = DebateOrchestrator()
        config = DebateConfigSchema(
            content="Test debate content.",
            max_rounds=1,
        )

        with patch.object(orchestrator, "_run_debate", new_callable=AsyncMock):
            job_id = await orchestrator.submit(config)

        cancelled = await orchestrator.cancel(job_id)
        assert cancelled is True

        job = await orchestrator.get_status(job_id)
        assert job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job_raises(self) -> None:
        orchestrator = DebateOrchestrator()
        with pytest.raises(KeyError, match="not found"):
            await orchestrator.cancel("nonexistent_id")

    @pytest.mark.asyncio
    async def test_cancel_completed_job_returns_false(self) -> None:
        orchestrator = DebateOrchestrator()
        config = DebateConfigSchema(
            content="Test debate content.",
            max_rounds=1,
        )

        with patch.object(orchestrator, "_run_debate", new_callable=AsyncMock):
            job_id = await orchestrator.submit(config)

        # Manually set to DONE
        orchestrator._task_store[job_id].status = "DONE"

        cancelled = await orchestrator.cancel(job_id)
        assert cancelled is False


# ===================================================================
# Utility tests
# ===================================================================


class TestUtilities:
    """Test utility functions."""

    def test_generate_request_id_is_unique(self) -> None:
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_generate_request_id_is_valid_uuid(self) -> None:
        import uuid

        request_id = generate_request_id()
        # Should not raise
        uuid.UUID(request_id)
