"""Comprehensive tests for debate_engine schemas.

Covers enum values, model instantiation, validation rules, defaults,
inheritance, and cross-field validators.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from debate_engine.schemas import (
    ConvergenceMode,
    ConsensusSchema,
    CritiqueConfigSchema,
    CritiqueSchema,
    DebateConfigSchema,
    DebateJobSchema,
    DebateMetadata,
    DefectType,
    ErrorDetail,
    FixKind,
    JobStatus,
    MinorityOpinion,
    ProviderMode,
    ProposalSchema,
    RejectedPosition,
    RevisionSchema,
    RoleStatus,
    Severity,
    TaskType,
    TerminationReason,
)


# ===================================================================
# Enum tests
# ===================================================================


class TestEnums:
    """Verify all enums have the expected values."""

    def test_task_type_values(self) -> None:
        assert set(TaskType) == {
            TaskType.CODE_REVIEW,
            TaskType.RAG_VALIDATION,
            TaskType.ARCHITECTURE_DECISION,
            TaskType.GENERAL_CRITIQUE,
            TaskType.AUTO,
        }

    def test_defect_type_values(self) -> None:
        assert DefectType.LOGICAL_FALLACY.value == "LOGICAL_FALLACY"
        assert DefectType.FACTUAL_ERROR.value == "FACTUAL_ERROR"
        assert DefectType.SECURITY_RISK.value == "SECURITY_RISK"

    def test_severity_values(self) -> None:
        assert set(Severity) == {Severity.CRITICAL, Severity.MAJOR, Severity.MINOR}

    def test_fix_kind_values(self) -> None:
        assert set(FixKind) == {
            FixKind.CONCRETE_FIX,
            FixKind.VALIDATION_STEP,
            FixKind.NEED_MORE_DATA,
        }

    def test_provider_mode_values(self) -> None:
        assert set(ProviderMode) == {
            ProviderMode.STABLE,
            ProviderMode.BALANCED,
            ProviderMode.DIVERSE,
        }

    def test_convergence_mode_values(self) -> None:
        assert set(ConvergenceMode) == {
            ConvergenceMode.CRITICAL_CLEARED,
            ConvergenceMode.MANUAL,
        }

    def test_job_status_values(self) -> None:
        assert set(JobStatus) == {
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.DONE,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    def test_termination_reason_values(self) -> None:
        assert set(TerminationReason) == {
            TerminationReason.COMPLETED,
            TerminationReason.QUORUM_FAILED,
            TerminationReason.JUDGE_FAILED,
            TerminationReason.COST_BUDGET_EXCEEDED,
            TerminationReason.CANCELLED,
            TerminationReason.TIMEOUT,
        }

    def test_role_status_values(self) -> None:
        assert set(RoleStatus) == {
            RoleStatus.SUCCESS,
            RoleStatus.PARSE_FAILED,
            RoleStatus.ROLE_FAILED,
        }


# ===================================================================
# CritiqueSchema tests
# ===================================================================


class TestCritiqueSchema:
    """Tests for individual agent critique schema."""

    def test_valid_instantiation(self) -> None:
        critique = CritiqueSchema(
            target_area="The introduction section of the proposal",
            defect_type=DefectType.LOGICAL_FALLACY,
            severity=Severity.MAJOR,
            evidence="The argument claims X implies Y, but there is no supporting data.",
            suggested_fix="Add statistical evidence or remove the causal claim.",
            fix_kind=FixKind.CONCRETE_FIX,
            confidence=0.85,
        )
        assert critique.target_area == "The introduction section of the proposal"
        assert critique.defect_type == DefectType.LOGICAL_FALLACY
        assert critique.severity == Severity.MAJOR
        assert critique.confidence == 0.85
        assert critique.is_devil_advocate is False
        assert critique.role_id is None
        assert critique.raw_response is None

    def test_default_values(self) -> None:
        critique = CritiqueSchema(
            target_area="A section of the document",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence="This is evidence supporting the critique finding.",
            suggested_fix="This is a suggested fix for the identified issue.",
            fix_kind=FixKind.VALIDATION_STEP,
            confidence=0.7,
        )
        assert critique.is_devil_advocate is False
        assert critique.role_id is None
        assert critique.raw_response is None

    def test_target_area_min_length(self) -> None:
        with pytest.raises(ValidationError, match="at least 10 characters"):
            CritiqueSchema(
                target_area="Short",
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="This is evidence supporting the critique finding.",
                suggested_fix="This is a suggested fix for the identified issue.",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=0.7,
            )

    def test_target_area_max_length(self) -> None:
        with pytest.raises(ValidationError, match="at most 200 characters"):
            CritiqueSchema(
                target_area="x" * 201,
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="This is evidence supporting the critique finding.",
                suggested_fix="This is a suggested fix for the identified issue.",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=0.7,
            )

    def test_evidence_min_length(self) -> None:
        with pytest.raises(ValidationError, match="at least 20 characters"):
            CritiqueSchema(
                target_area="A section of the document",
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="Too short",
                suggested_fix="This is a suggested fix for the identified issue.",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=0.7,
            )

    def test_suggested_fix_min_length(self) -> None:
        with pytest.raises(ValidationError, match="at least 20 characters"):
            CritiqueSchema(
                target_area="A section of the document",
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="This is evidence supporting the critique finding.",
                suggested_fix="Too short",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=0.7,
            )

    def test_confidence_range(self) -> None:
        # Below minimum
        with pytest.raises(ValidationError):
            CritiqueSchema(
                target_area="A section of the document",
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="This is evidence supporting the critique finding.",
                suggested_fix="This is a suggested fix for the identified issue.",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=-0.1,
            )
        # Above maximum
        with pytest.raises(ValidationError):
            CritiqueSchema(
                target_area="A section of the document",
                defect_type=DefectType.GENERAL,
                severity=Severity.MINOR,
                evidence="This is evidence supporting the critique finding.",
                suggested_fix="This is a suggested fix for the identified issue.",
                fix_kind=FixKind.VALIDATION_STEP,
                confidence=1.1,
            )
        # Boundary values should work
        CritiqueSchema(
            target_area="A section of the document",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence="This is evidence supporting the critique finding.",
            suggested_fix="This is a suggested fix for the identified issue.",
            fix_kind=FixKind.VALIDATION_STEP,
            confidence=0.0,
        )
        CritiqueSchema(
            target_area="A section of the document",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence="This is evidence supporting the critique finding.",
            suggested_fix="This is a suggested fix for the identified issue.",
            fix_kind=FixKind.VALIDATION_STEP,
            confidence=1.0,
        )

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CritiqueSchema()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "target_area" in field_names
        assert "defect_type" in field_names
        assert "severity" in field_names
        assert "evidence" in field_names
        assert "suggested_fix" in field_names
        assert "fix_kind" in field_names
        assert "confidence" in field_names

    def test_devil_advocate_flag(self) -> None:
        critique = CritiqueSchema(
            target_area="A section of the document",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence="This is evidence supporting the critique finding.",
            suggested_fix="This is a suggested fix for the identified issue.",
            fix_kind=FixKind.VALIDATION_STEP,
            confidence=0.7,
            is_devil_advocate=True,
        )
        assert critique.is_devil_advocate is True


# ===================================================================
# ConsensusSchema tests
# ===================================================================


class TestConsensusSchema:
    """Tests for the aggregated consensus result schema."""

    def _make_metadata(self, **overrides: object) -> dict[str, object]:
        defaults: dict[str, object] = {
            "task_type": TaskType.GENERAL_CRITIQUE,
            "provider_mode": ProviderMode.STABLE,
            "quorum_achieved": True,
            "termination_reason": TerminationReason.COMPLETED,
        }
        defaults.update(overrides)
        return defaults

    def _make_valid_consensus(self, **overrides: object) -> dict[str, object]:
        defaults: dict[str, object] = {
            "final_conclusion": "A comprehensive synthesized conclusion covering all key points.",
            "consensus_confidence": 0.85,
            "remaining_disagreements": ["Minor disagreement on methodology"],
            "disagreement_confirmation": "All disagreements actively reviewed.",
            "debate_metadata": DebateMetadata(**self._make_metadata()),
        }
        defaults.update(overrides)
        return defaults

    def test_valid_consensus(self) -> None:
        consensus = ConsensusSchema(**self._make_valid_consensus())
        assert consensus.consensus_confidence == 0.85
        assert consensus.partial_return is False
        assert consensus.adopted_contributions == {}
        assert consensus.rejected_positions == []
        assert consensus.preserved_minority_opinions == []
        assert consensus.critiques_summary == []

    def test_consensus_confidence_max_0_95(self) -> None:
        with pytest.raises(ValidationError, match="less than or equal to 0.95"):
            ConsensusSchema(**self._make_valid_consensus(consensus_confidence=0.99))

        # 0.95 should be accepted
        ConsensusSchema(**self._make_valid_consensus(consensus_confidence=0.95))

    def test_partial_return_requires_critiques_summary(self) -> None:
        with pytest.raises(ValidationError, match="critiques_summary must be non-empty"):
            ConsensusSchema(**self._make_valid_consensus(partial_return=True))

        # With non-empty summary, it should work
        critique = CritiqueSchema(
            target_area="A section of the document",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence="This is evidence supporting the critique finding.",
            suggested_fix="This is a suggested fix for the identified issue.",
            fix_kind=FixKind.VALIDATION_STEP,
            confidence=0.7,
        )
        ConsensusSchema(
            **self._make_valid_consensus(
                partial_return=True,
                critiques_summary=[critique],
            ),
        )

    def test_disagreement_confirmation_required_when_no_disagreements(self) -> None:
        with pytest.raises(ValidationError, match="disagreement_confirmation is required"):
            ConsensusSchema(
                **self._make_valid_consensus(
                    remaining_disagreements=[],
                    disagreement_confirmation=None,
                ),
            )

        # With confirmation, it should work
        ConsensusSchema(
            **self._make_valid_consensus(
                remaining_disagreements=[],
                disagreement_confirmation="Reviewed: no disagreements found.",
            ),
        )

    def test_with_adopted_contributions(self) -> None:
        consensus = ConsensusSchema(
            **self._make_valid_consensus(),
            adopted_contributions={
                "ROLE_A": ["Improved error handling", "Better test coverage"],
                "ROLE_B": ["Security hardening"],
            },
        )
        assert len(consensus.adopted_contributions) == 2

    def test_with_rejected_positions(self) -> None:
        rejected = RejectedPosition(
            claim="We should use MongoDB",
            rejection_reason="PostgreSQL better fits the relational data model.",
        )
        consensus = ConsensusSchema(
            **self._make_valid_consensus(),
            rejected_positions=[rejected],
        )
        assert len(consensus.rejected_positions) == 1

    def test_with_minority_opinions(self) -> None:
        opinion = MinorityOpinion(
            opinion="I believe the caching strategy is premature.",
            source_role="ROLE_B",
            source_critique_severity=Severity.MAJOR,
            potential_risk_if_ignored="Performance degradation under load.",
        )
        consensus = ConsensusSchema(
            **self._make_valid_consensus(),
            preserved_minority_opinions=[opinion],
        )
        assert len(consensus.preserved_minority_opinions) == 1


# ===================================================================
# CritiqueConfigSchema tests
# ===================================================================


class TestCritiqueConfigSchema:
    """Tests for the critique configuration schema."""

    def test_defaults(self) -> None:
        config = CritiqueConfigSchema(
            content="This is a well-structured proposal for the new API endpoint."
        )
        assert config.task_type == TaskType.AUTO
        assert config.provider_mode == ProviderMode.STABLE
        assert config.enable_devil_advocate is True
        assert config.cost_budget_usd == 0.30
        assert config.custom_role_prompts is None

    def test_content_min_length(self) -> None:
        with pytest.raises(ValidationError, match="at least 10 characters"):
            CritiqueConfigSchema(content="Short")

    def test_content_max_length(self) -> None:
        with pytest.raises(ValidationError, match="at most 8000 characters"):
            CritiqueConfigSchema(content="x" * 8001)

    def test_cost_budget_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            CritiqueConfigSchema(
                content="This is a well-structured proposal for the new API endpoint.",
                cost_budget_usd=0.0,
            )

    def test_custom_task_type(self) -> None:
        config = CritiqueConfigSchema(
            content="This is a well-structured proposal for the new API endpoint.",
            task_type=TaskType.CODE_REVIEW,
        )
        assert config.task_type == TaskType.CODE_REVIEW

    def test_custom_provider_mode(self) -> None:
        config = CritiqueConfigSchema(
            content="This is a well-structured proposal for the new API endpoint.",
            provider_mode=ProviderMode.BALANCED,
        )
        assert config.provider_mode == ProviderMode.BALANCED

    def test_custom_role_prompts(self) -> None:
        config = CritiqueConfigSchema(
            content="This is a well-structured proposal for the new API endpoint.",
            custom_role_prompts={"ROLE_A": "Be extra critical."},
        )
        assert config.custom_role_prompts == {"ROLE_A": "Be extra critical."}


# ===================================================================
# DebateConfigSchema tests
# ===================================================================


class TestDebateConfigSchema:
    """Tests for the debate configuration schema (extends CritiqueConfigSchema)."""

    def test_extends_critique_config(self) -> None:
        config = DebateConfigSchema(
            content="This is a well-structured proposal for the new API endpoint."
        )
        # Should inherit all CritiqueConfigSchema defaults
        assert config.content == "This is a well-structured proposal for the new API endpoint."
        assert config.task_type == TaskType.AUTO
        assert config.provider_mode == ProviderMode.STABLE

    def test_debate_specific_defaults(self) -> None:
        config = DebateConfigSchema(
            content="This is a well-structured proposal for the new API endpoint."
        )
        assert config.max_rounds == 2
        assert config.convergence_mode == ConvergenceMode.CRITICAL_CLEARED
        assert config.revision_instructions is None

    def test_max_rounds_range(self) -> None:
        with pytest.raises(ValidationError):
            DebateConfigSchema(
                content="This is a well-structured proposal for the new API endpoint.",
                max_rounds=0,
            )
        with pytest.raises(ValidationError):
            DebateConfigSchema(
                content="This is a well-structured proposal for the new API endpoint.",
                max_rounds=3,
            )

    def test_revision_instructions_optional(self) -> None:
        config = DebateConfigSchema(
            content="This is a well-structured proposal for the new API endpoint.",
            revision_instructions="Focus on security implications.",
        )
        assert config.revision_instructions == "Focus on security implications."


# ===================================================================
# DebateJobSchema tests
# ===================================================================


class TestDebateJobSchema:
    """Tests for the debate job tracking schema."""

    def test_valid_construction(self) -> None:
        now = datetime.now(timezone.utc)
        metadata = DebateMetadata(
            task_type=TaskType.GENERAL_CRITIQUE,
            provider_mode=ProviderMode.STABLE,
            quorum_achieved=True,
            termination_reason=TerminationReason.COMPLETED,
        )
        consensus = ConsensusSchema(
            final_conclusion="A conclusion.",
            consensus_confidence=0.9,
            remaining_disagreements=[],
            disagreement_confirmation="No disagreements.",
            debate_metadata=metadata,
        )
        job = DebateJobSchema(
            job_id="test-job-123",
            status=JobStatus.DONE,
            created_at=now,
            updated_at=now,
            current_round=2,
            current_phase="completed",
            progress_pct=100,
            result=consensus,
            cost_so_far_usd=0.05,
        )
        assert job.status == JobStatus.DONE
        assert job.current_round == 2
        assert job.cost_so_far_usd == 0.05
        assert job.result is not None

    def test_error_detail(self) -> None:
        error = ErrorDetail(
            message="LLM provider unavailable",
            code="PROVIDER_ERROR",
        )
        assert error.message == "LLM provider unavailable"
        assert error.code == "PROVIDER_ERROR"

    def test_job_with_error(self) -> None:
        now = datetime.now(timezone.utc)
        error = ErrorDetail(
            message="Cost budget exceeded",
            code="COST_BUDGET_EXCEEDED",
        )
        job = DebateJobSchema(
            job_id="test-job-456",
            status=JobStatus.FAILED,
            created_at=now,
            updated_at=now,
            error=error,
        )
        assert job.status == JobStatus.FAILED
        assert job.error.message == "Cost budget exceeded"

    def test_progress_pct_range(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            DebateJobSchema(
                job_id="test-job",
                status=JobStatus.RUNNING,
                created_at=now,
                updated_at=now,
                progress_pct=101,
            )


# ===================================================================
# ProposalSchema tests
# ===================================================================


class TestProposalSchema:
    """Tests for the proposal and revision schemas."""

    def test_valid_proposal(self) -> None:
        proposal = ProposalSchema(
            role_id="ROLE_A",
            core_claim="The system should use event-driven architecture.",
            supporting_arguments=["Better scalability", "Loose coupling"],
            confidence_level=0.85,
        )
        assert proposal.role_id == "ROLE_A"
        assert proposal.is_devil_advocate is False
        assert len(proposal.supporting_arguments) == 2

    def test_revision_extends_proposal(self) -> None:
        revision = RevisionSchema(
            role_id="ROLE_A",
            core_claim="The system should use event-driven architecture.",
            supporting_arguments=["Better scalability"],
            confidence_level=0.9,
            changes_from_previous="Increased confidence based on cross-critique feedback.",
        )
        assert revision.changes_from_previous != ""
        assert revision.confidence_level == 0.9
