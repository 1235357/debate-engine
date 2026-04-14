"""DebateOrchestrator -- the v0.2 async multi-round debate engine.

Manages multi-round debate workflows as background asyncio tasks with
job_id-based status tracking, cancellation, and auto-cleanup.

Workflow:
  Round 1: Proposals -> Cross-critiques -> Anonymize -> Quorum
  Convergence check (CRITICAL_CLEARED mode)
  Round 2 (if needed): Revisions -> Cross-critiques -> Anonymize -> Quorum
  Final: Judge summarization
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from ..api.key_manager import APIKeyManager
from ..providers.config import ProviderConfig
from ..providers.llm_provider import CallResult, LLMProvider
from ..storage import RedisStorage
from .base import (
    anonymize_critiques,
    build_judge_summary,
    build_role_system_prompt,
    check_quorum,
    generate_request_id,
)
from .role_templates import JUDGE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal job representation
# ---------------------------------------------------------------------------


@dataclass
class DebateJob:
    """Internal bookkeeping for a single debate task."""

    job_id: str
    config: Any  # DebateConfigSchema
    status: Literal["PENDING", "RUNNING", "DONE", "FAILED", "CANCELLED"] = "PENDING"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    current_round: int = 0
    current_phase: str = "initialized"
    progress_pct: int = 0
    result: Any = None  # ConsensusSchema | None
    error: str | None = None
    cost_so_far_usd: float = 0.0
    cancel_requested: bool = False

    def to_schema(self) -> Any:
        """Convert to the public ``DebateJobSchema``."""
        from debate_engine.schemas import (
            DebateJobSchema,
            ErrorDetail,
            JobStatus,
        )

        # Map internal status string to JobStatus enum
        status_map: dict[str, JobStatus] = {
            "PENDING": JobStatus.PENDING,
            "RUNNING": JobStatus.RUNNING,
            "DONE": JobStatus.DONE,
            "FAILED": JobStatus.FAILED,
            "CANCELLED": JobStatus.CANCELLED,
        }
        job_status = status_map.get(self.status, JobStatus.FAILED)

        error_detail = None
        if self.error:
            error_detail = ErrorDetail(
                message=self.error,
                code=self.status,
            )

        return DebateJobSchema(
            job_id=self.job_id,
            status=job_status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            current_round=self.current_round,
            current_phase=self.current_phase,
            progress_pct=self.progress_pct,
            result=self.result,
            error=error_detail,
            cost_so_far_usd=round(self.cost_so_far_usd, 6),
        )

    def touch(self) -> None:
        """Update the ``updated_at`` timestamp."""
        self.updated_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# DebateOrchestrator
# ---------------------------------------------------------------------------

# How long completed/failed/cancelled jobs are kept in memory
_JOB_RETENTION_SECONDS = 3600  # 1 hour


class DebateOrchestrator:
    """v0.2 async multi-round debate engine with job management.

    Parameters
    ----------
    provider_config:
        Provider configuration.  When ``None``, :meth:`ProviderConfig.from_env`
        is used.
    """

    def __init__(
        self,
        provider_config: ProviderConfig | None = None,
        key_manager: APIKeyManager | None = None,
    ) -> None:
        self.provider = LLMProvider(
            provider_config or ProviderConfig.from_env(), key_manager=key_manager
        )
        self._task_store: dict[str, DebateJob] = {}
        self._cleanup_task: asyncio.Task | None = None
        # Initialize Redis storage
        import os

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._storage = RedisStorage(redis_url)
        # Load jobs from Redis on startup
        self._load_jobs_from_storage()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(self, config: Any) -> str:
        """Submit a debate task and return the job_id.

        The debate runs in a background ``asyncio.Task``.

        Parameters
        ----------
        config:
            A ``DebateConfigSchema`` instance.

        Returns
        -------
        str
            The job UUID.
        """
        job_id = generate_request_id()
        job = DebateJob(job_id=job_id, config=config)
        self._task_store[job_id] = job

        # Ensure cleanup loop is running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Launch background debate
        asyncio.create_task(self._run_debate(job_id, config))

        logger.info("Debate job submitted: job_id=%s", job_id)
        return job_id

    async def get_status(self, job_id: str) -> Any:
        """Get the current status of a debate job.

        Returns
        -------
        DebateJobSchema
            The public job status object.

        Raises
        ------
        KeyError
            If the job_id is not found.
        """
        job = self._task_store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")
        job.cost_so_far_usd = self.provider.cost_accumulated
        return job.to_schema()

    async def get_result(self, job_id: str) -> Any | None:
        """Get the result of a completed debate job.

        Returns ``None`` if the job has not completed yet.

        Returns
        -------
        ConsensusSchema | None
        """
        job = self._task_store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")
        return job.result

    async def cancel(self, job_id: str) -> bool:
        """Cancel a running debate task.

        If the task is PENDING it is cancelled immediately.  If RUNNING, a
        cancellation signal is set and the task will stop after the current
        LLM call completes.

        Returns
        -------
        bool
            ``True`` if cancellation was successfully requested.
        """
        job = self._task_store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")

        if job.status in ("DONE", "FAILED", "CANCELLED"):
            logger.info("Job %s already in terminal state: %s", job_id, job.status)
            return False

        job.cancel_requested = True
        job.status = "CANCELLED"
        job.touch()
        # Save to Redis
        self._storage.save_job(job)
        logger.info(
            "Cancel requested for job_id=%s cost_so_far=%.6f",
            job_id,
            self.provider.cost_accumulated,
        )
        return True

    def _load_jobs_from_storage(self) -> None:
        """Load jobs from Redis storage on startup."""
        try:
            job_ids = self._storage.list_jobs()
            for job_id in job_ids:
                job = self._storage.get_job(job_id)
                if job:
                    # Only load jobs that are not in terminal state
                    if job.status not in ("DONE", "FAILED", "CANCELLED"):
                        self._task_store[job_id] = job
                        logger.info("Loaded job %s from storage", job_id)
        except Exception as exc:
            logger.warning("Failed to load jobs from storage: %s", exc)

    # ------------------------------------------------------------------
    # Background debate execution
    # ------------------------------------------------------------------

    async def _run_debate(self, job_id: str, config: Any) -> None:
        """Background task: run the full multi-round debate."""
        job = self._task_store.get(job_id)
        if job is None:
            return

        try:
            job.status = "RUNNING"
            job.touch()
            # Save to Redis
            self._storage.save_job(job)

            # Lazy imports
            from debate_engine.schemas import (
                ConsensusSchema,
                DebateMetadata,
                TerminationReason,
            )
            from debate_engine.schemas import (
                ProviderMode as SchemaProviderMode,
            )
            from debate_engine.schemas import (
                TaskType as SchemaTaskType,
            )

            request_id = job_id
            start_time = time.monotonic()

            # Resolve task type
            raw_task_type = config.task_type
            task_type_str = self._resolve_task_type(raw_task_type)
            if task_type_str == "AUTO":
                from .quick_critique import _auto_detect_task_type

                task_type_str = _auto_detect_task_type(config.content)

            try:
                task_type_enum = SchemaTaskType(task_type_str)
            except ValueError:
                task_type_enum = SchemaTaskType.GENERAL_CRITIQUE

            provider_mode_str = self.provider.config.mode.value
            try:
                provider_mode_enum = SchemaProviderMode(provider_mode_str)
            except ValueError:
                provider_mode_enum = SchemaProviderMode.STABLE

            enable_da = getattr(config, "enable_devil_advocate", True)
            cost_budget = getattr(config, "cost_budget_usd", 0.80)
            max_rounds = getattr(config, "max_rounds", 2)
            convergence_mode = getattr(config, "convergence_mode", "CRITICAL_CLEARED")
            custom_prompts = getattr(config, "custom_role_prompts", None) or {}

            # Normalize convergence_mode to string for comparison
            conv_mode_str = (
                convergence_mode.value
                if hasattr(convergence_mode, "value")
                else str(convergence_mode)
            )

            roles = ["ROLE_A", "ROLE_B", "DA_ROLE"] if enable_da else ["ROLE_A", "ROLE_B", "ROLE_C"]
            role_types = (
                ["critic_a", "critic_b", "devil_advocate"]
                if enable_da
                else ["critic_a", "critic_b", "critic_c"]
            )

            models_used: set[str] = set()
            total_parse_attempts = 0
            all_critiques: list[Any] = []
            rounds_data: list[dict[str, Any]] = []

            # ==============================================================
            # Round 1: Proposals -> Cross-critiques -> Anonymize -> Quorum
            # ==============================================================
            if self._should_cancel(job):
                return

            job.current_round = 1
            job.current_phase = "round1_proposals"
            job.progress_pct = 10
            job.touch()
            # Save to Redis
            self._storage.save_job(job)

            # Generate proposals
            proposals = await self._generate_proposals(
                roles=roles,
                role_types=role_types,
                task_type=task_type_str,
                content=config.content,
                custom_prompts=custom_prompts,
                cost_budget=cost_budget,
            )

            for p, cr in proposals:
                total_parse_attempts += cr.parse_attempts
                if cr.model_used:
                    models_used.add(cr.model_used)

            if self._should_cancel(job):
                return

            job.current_phase = "round1_critiques"
            job.progress_pct = 30
            job.touch()
            # Save to Redis
            self._storage.save_job(job)

            # Cross-critique proposals
            r1_critiques, r1_results = await self._cross_critique(
                proposals=proposals,
                roles=roles,
                role_types=role_types,
                task_type=task_type_str,
                custom_prompts=custom_prompts,
                cost_budget=cost_budget,
            )

            for cr in r1_results:
                total_parse_attempts += cr.parse_attempts
                if cr.model_used:
                    models_used.add(cr.model_used)

            all_critiques.extend(r1_critiques)

            # Anonymize
            r1_anonymized = anonymize_critiques(r1_critiques)

            # Quorum
            quorum_met, success_count = check_quorum(r1_results)

            rounds_data.append(
                {
                    "round": 1,
                    "critiques_count": len(r1_critiques),
                    "quorum_met": quorum_met,
                    "success_count": success_count,
                }
            )

            if self._should_cancel(job):
                return

            # ==============================================================
            # Convergence check
            # ==============================================================
            need_round2 = False
            if max_rounds >= 2 and quorum_met:
                if conv_mode_str == "CRITICAL_CLEARED":
                    critical_count = sum(
                        1
                        for c in r1_critiques
                        if getattr(c, "severity", None) == "CRITICAL"
                        or (
                            hasattr(c, "severity")
                            and hasattr(c.severity, "value")
                            and c.severity.value == "CRITICAL"
                        )
                    )
                    if critical_count > 0:
                        need_round2 = True
                        logger.info(
                            "Convergence not reached: %d CRITICAL critiques in round 1",
                            critical_count,
                        )
                    else:
                        logger.info("Convergence reached: no CRITICAL in round 1")
                else:
                    # MANUAL mode: always run round 2
                    need_round2 = True

            # ==============================================================
            # Round 2 (if needed)
            # ==============================================================
            if need_round2 and not self._should_cancel(job):
                job.current_round = 2
                job.current_phase = "round2_revisions"
                job.progress_pct = 50
                job.touch()
                # Save to Redis
                self._storage.save_job(job)

                # Generate revisions based on round 1 critiques
                revisions = await self._generate_revisions(
                    proposals=proposals,
                    anonymized_critiques=r1_anonymized,
                    roles=roles,
                    role_types=role_types,
                    task_type=task_type_str,
                    custom_prompts=custom_prompts,
                    revision_instructions=getattr(config, "revision_instructions", None),
                    cost_budget=cost_budget,
                )

                for p, cr in revisions:
                    total_parse_attempts += cr.parse_attempts
                    if cr.model_used:
                        models_used.add(cr.model_used)

                if self._should_cancel(job):
                    return

                job.current_phase = "round2_critiques"
                job.progress_pct = 70
                job.touch()
                # Save to Redis
                self._storage.save_job(job)

                # Cross-critique revisions
                r2_critiques, r2_results = await self._cross_critique(
                    proposals=revisions,
                    roles=roles,
                    role_types=role_types,
                    task_type=task_type_str,
                    custom_prompts=custom_prompts,
                    cost_budget=cost_budget,
                )

                for cr in r2_results:
                    total_parse_attempts += cr.parse_attempts
                    if cr.model_used:
                        models_used.add(cr.model_used)

                all_critiques.extend(r2_critiques)
                r2_anonymized = anonymize_critiques(r2_critiques)
                r2_quorum, r2_success = check_quorum(r2_results)

                rounds_data.append(
                    {
                        "round": 2,
                        "critiques_count": len(r2_critiques),
                        "quorum_met": r2_quorum,
                        "success_count": r2_success,
                    }
                )

                # Use round 2 results for judge
                final_anonymized = r2_anonymized
                final_quorum = r2_quorum
                final_success = r2_success
            else:
                final_anonymized = r1_anonymized
                final_quorum = quorum_met
                final_success = success_count

            if self._should_cancel(job):
                return

            # ==============================================================
            # Final: Judge summarization
            # ==============================================================
            job.current_phase = "judge_summarization"
            job.progress_pct = 85
            job.touch()
            # Save to Redis
            self._storage.save_job(job)

            if not final_quorum:
                job.status = "DONE"
                job.result = self._build_partial_result(
                    request_id=request_id,
                    job_id=job_id,
                    task_type_enum=task_type_enum,
                    provider_mode_enum=provider_mode_enum,
                    start_time=start_time,
                    critiques=final_anonymized,
                    models_used=models_used,
                    total_parse_attempts=total_parse_attempts,
                    rounds_completed=job.current_round,
                    termination_reason=TerminationReason.QUORUM_FAILED,
                )
                job.progress_pct = 100
                job.touch()
                # Save to Redis
                self._storage.save_job(job)
                return

            if self.provider.cost_accumulated >= cost_budget:
                job.status = "DONE"
                job.result = self._build_partial_result(
                    request_id=request_id,
                    job_id=job_id,
                    task_type_enum=task_type_enum,
                    provider_mode_enum=provider_mode_enum,
                    start_time=start_time,
                    critiques=final_anonymized,
                    models_used=models_used,
                    total_parse_attempts=total_parse_attempts,
                    rounds_completed=job.current_round,
                    termination_reason=TerminationReason.COST_BUDGET_EXCEEDED,
                )
                job.progress_pct = 100
                job.touch()
                # Save to Redis
                self._storage.save_job(job)
                return

            judge_summary = build_judge_summary(final_anonymized, (final_quorum, final_success))

            # Include round history in judge context if multi-round
            if len(rounds_data) > 1:
                round_history_text = "\n\n## Debate Round History\n"
                for rd in rounds_data:
                    round_history_text += (
                        f"- Round {rd['round']}: {rd['critiques_count']} critiques, "
                        f"quorum={'met' if rd['quorum_met'] else 'not met'}, "
                        f"{rd['success_count']} successful reviewers\n"
                    )
                judge_summary += round_history_text

            judge_parsed, judge_result = await self.provider.call(
                messages=[{"role": "user", "content": judge_summary}],
                system_prompt=JUDGE_SYSTEM_PROMPT,
                response_model=ConsensusSchema,
                role_type="judge",
                temperature=0.2,
            )

            total_parse_attempts += judge_result.parse_attempts
            if judge_result.model_used:
                models_used.add(judge_result.model_used)

            if judge_result.status != "SUCCESS" or judge_parsed is None:
                job.status = "DONE"
                job.result = self._build_partial_result(
                    request_id=request_id,
                    job_id=job_id,
                    task_type_enum=task_type_enum,
                    provider_mode_enum=provider_mode_enum,
                    start_time=start_time,
                    critiques=final_anonymized,
                    models_used=models_used,
                    total_parse_attempts=total_parse_attempts,
                    rounds_completed=job.current_round,
                    termination_reason=TerminationReason.JUDGE_FAILED,
                )
                job.progress_pct = 100
                job.touch()
                return

            # ==============================================================
            # Success
            # ==============================================================
            total_latency_ms = (time.monotonic() - start_time) * 1000
            total_cost = self.provider.cost_accumulated

            metadata = DebateMetadata(
                request_id=request_id,
                job_id=job_id,
                task_type=task_type_enum,
                provider_mode=provider_mode_enum,
                rounds_completed=job.current_round,
                total_cost_usd=round(total_cost, 6),
                total_latency_ms=round(total_latency_ms, 1),
                models_used=list(models_used),
                quorum_achieved=final_quorum,
                termination_reason=TerminationReason.COMPLETED,
                parse_attempts_total=total_parse_attempts,
            )

            final = judge_parsed.model_copy(
                update={
                    "debate_metadata": metadata,
                    "critiques_summary": final_anonymized,
                    "partial_return": False,
                }
            )

            # Cap confidence
            if hasattr(final, "consensus_confidence") and final.consensus_confidence > 0.95:
                final = final.model_copy(update={"consensus_confidence": 0.95})

            job.status = "DONE"
            job.result = final
            job.progress_pct = 100
            job.touch()
            # Save to Redis
            self._storage.save_job(job)

            logger.info(
                "Debate completed: job_id=%s rounds=%d cost=%.6f latency=%.0fms",
                job_id,
                job.current_round,
                total_cost,
                total_latency_ms,
            )

        except asyncio.CancelledError:
            job.status = "CANCELLED"
            job.touch()
            # Save to Redis
            self._storage.save_job(job)
            logger.info("Debate cancelled: job_id=%s", job_id)
        except Exception as exc:
            job.status = "FAILED"
            job.error = str(exc)
            job.touch()
            # Save to Redis
            self._storage.save_job(job)
            logger.exception("Debate failed: job_id=%s error=%s", job_id, exc)

    # ------------------------------------------------------------------
    # Proposal / revision generation
    # ------------------------------------------------------------------

    async def _generate_proposals(
        self,
        roles: list[str],
        role_types: list[str],
        task_type: str,
        content: str,
        custom_prompts: dict[str, str],
        cost_budget: float,
    ) -> list[tuple[Any, CallResult]]:
        """Generate initial proposals from each role."""
        from debate_engine.schemas import ProposalSchema

        async def _propose(role: str, role_type: str) -> tuple[Any, CallResult]:
            system_prompt = build_role_system_prompt(
                role_type=role,
                task_type=task_type,
                custom_prompt=custom_prompts.get(role),
            )
            user_msg = {
                "role": "user",
                "content": (
                    "Review the following content and provide your initial "
                    "assessment as a structured proposal. Output a valid JSON "
                    "object matching the ProposalSchema.\n\n"
                    f"--- Content ---\n{content}\n--- End ---"
                ),
            }
            return await self.provider.call(
                messages=[user_msg],
                system_prompt=system_prompt,
                response_model=ProposalSchema,
                role_type=role_type,
                temperature=0.4,
            )

        if self.provider.cost_accumulated >= cost_budget:
            return []

        results = await asyncio.gather(
            *[_propose(r, rt) for r, rt in zip(roles, role_types)],
            return_exceptions=True,
        )

        proposals: list[tuple[Any, CallResult]] = []
        for idx, res in enumerate(results):
            if isinstance(res, BaseException):
                proposals.append(
                    (
                        None,
                        CallResult(
                            status="ROLE_FAILED",
                            error_message=str(res),
                            model_used="unknown",
                        ),
                    )
                )
            else:
                proposals.append(res)
        return proposals

    async def _generate_revisions(
        self,
        proposals: list[tuple[Any, CallResult]],
        anonymized_critiques: list[Any],
        roles: list[str],
        role_types: list[str],
        task_type: str,
        custom_prompts: dict[str, str],
        revision_instructions: str | None,
        cost_budget: float,
    ) -> list[tuple[Any, CallResult]]:
        """Generate revised proposals based on cross-critiques."""
        from debate_engine.schemas import ProposalSchema

        # Build a summary of anonymized critiques for revision context
        critique_text = "\n".join(
            f"- [{getattr(c, 'role_id', '?')}] {getattr(c, 'target_area', '?')}: "
            f"{getattr(c, 'defect_type', '?')} ({getattr(c, 'severity', '?')}) -- "
            f"{getattr(c, 'evidence', '')[:200]}"
            for c in anonymized_critiques
        )

        async def _revise(idx: int, role: str, role_type: str) -> tuple[Any, CallResult]:
            original_proposal = proposals[idx][0] if proposals[idx][0] else "(unavailable)"
            system_prompt = build_role_system_prompt(
                role_type=role,
                task_type=task_type,
                custom_prompt=custom_prompts.get(role),
            )
            user_msg = {
                "role": "user",
                "content": (
                    "Based on the cross-critiques below, revise your initial "
                    "proposal. Output a valid JSON object matching the "
                    "ProposalSchema with the `changes_from_previous` field "
                    "describing what you changed and why.\n\n"
                    f"--- Your Original Proposal ---\n{original_proposal}\n"
                    f"--- End ---\n\n"
                    f"--- Cross-Critiques (anonymized) ---\n{critique_text}\n"
                    f"--- End ---"
                    + (
                        f"\n\n--- Revision Instructions ---\n{revision_instructions}\n--- End ---"
                        if revision_instructions
                        else ""
                    )
                ),
            }
            return await self.provider.call(
                messages=[user_msg],
                system_prompt=system_prompt,
                response_model=ProposalSchema,
                role_type=role_type,
                temperature=0.3,
            )

        if self.provider.cost_accumulated >= cost_budget:
            return []

        results = await asyncio.gather(
            *[_revise(i, r, rt) for i, (r, rt) in enumerate(zip(roles, role_types))],
            return_exceptions=True,
        )

        revisions: list[tuple[Any, CallResult]] = []
        for idx, res in enumerate(results):
            if isinstance(res, BaseException):
                revisions.append(
                    (
                        None,
                        CallResult(
                            status="ROLE_FAILED",
                            error_message=str(res),
                            model_used="unknown",
                        ),
                    )
                )
            else:
                revisions.append(res)
        return revisions

    # ------------------------------------------------------------------
    # Cross-critique
    # ------------------------------------------------------------------

    async def _cross_critique(
        self,
        proposals: list[tuple[Any, CallResult]],
        roles: list[str],
        role_types: list[str],
        task_type: str,
        custom_prompts: dict[str, str],
        cost_budget: float,
    ) -> tuple[list[Any], list[CallResult]]:
        """Each role critiques the other roles' proposals."""
        from debate_engine.schemas import CritiqueSchema

        async def _critique(idx: int, role: str, role_type: str) -> tuple[Any, CallResult]:
            others_text = ""
            for j, (prop, cr) in enumerate(proposals):
                if j == idx or prop is None:
                    continue
                others_text += f"\n### Proposal from another reviewer:\n{prop}\n"

            if not others_text:
                others_text = "(No other proposals available for cross-critique)"

            system_prompt = build_role_system_prompt(
                role_type=role,
                task_type=task_type,
                custom_prompt=custom_prompts.get(role),
            )
            user_msg = {
                "role": "user",
                "content": (
                    "Critique the following proposals from other reviewers. "
                    "Output a valid JSON object matching the CritiqueSchema.\n\n"
                    f"--- Other Proposals ---\n{others_text}\n--- End ---"
                ),
            }
            return await self.provider.call(
                messages=[user_msg],
                system_prompt=system_prompt,
                response_model=CritiqueSchema,
                role_type=role_type,
                temperature=0.3,
            )

        if self.provider.cost_accumulated >= cost_budget:
            return [], []

        results = await asyncio.gather(
            *[_critique(i, r, rt) for i, (r, rt) in enumerate(zip(roles, role_types))],
            return_exceptions=True,
        )

        critiques: list[Any] = []
        call_results: list[CallResult] = []
        for idx, res in enumerate(results):
            if isinstance(res, BaseException):
                call_results.append(
                    CallResult(
                        status="ROLE_FAILED",
                        error_message=str(res),
                        model_used="unknown",
                    )
                )
                continue

            parsed, cr = res
            call_results.append(cr)
            if cr.status == "SUCCESS" and parsed is not None:
                if hasattr(parsed, "role_id"):
                    parsed = parsed.model_copy(update={"role_id": roles[idx]})
                critiques.append(parsed)
            elif cr.status == "PARSE_FAILED" and parsed is not None:
                if hasattr(parsed, "role_id"):
                    parsed = parsed.model_copy(update={"role_id": roles[idx]})
                critiques.append(parsed)

        return critiques, call_results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _should_cancel(self, job: DebateJob) -> bool:
        """Check if cancellation has been requested."""
        if job.cancel_requested:
            job.status = "CANCELLED"
            job.touch()
            logger.info("Debate cancelled mid-execution: job_id=%s", job.job_id)
            return True
        return False

    @staticmethod
    def _resolve_task_type(raw: Any) -> str:
        """Normalize task_type to a plain string."""
        if hasattr(raw, "value"):
            return str(raw.value)
        return str(raw)

    def _build_partial_result(
        self,
        *,
        request_id: str,
        job_id: str,
        task_type_enum: Any,
        provider_mode_enum: Any,
        start_time: float,
        critiques: list[Any],
        models_used: set[str],
        total_parse_attempts: int,
        rounds_completed: int,
        termination_reason: Any,
    ) -> Any:
        """Build a partial ConsensusSchema."""
        from debate_engine.schemas import (
            ConsensusSchema,
            DebateMetadata,
        )

        total_latency_ms = (time.monotonic() - start_time) * 1000
        total_cost = self.provider.cost_accumulated

        metadata = DebateMetadata(
            request_id=request_id,
            job_id=job_id,
            task_type=task_type_enum,
            provider_mode=provider_mode_enum,
            rounds_completed=rounds_completed,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(total_latency_ms, 1),
            models_used=list(models_used),
            quorum_achieved=False,
            termination_reason=termination_reason,
            parse_attempts_total=total_parse_attempts,
        )

        reason_str = (
            str(termination_reason.value)
            if hasattr(termination_reason, "value")
            else str(termination_reason)
        )

        if "QUORUM" in reason_str:
            conclusion = (
                "Quorum not met during debate. The following partial "
                "critique results are provided for reference."
            )
        elif "COST" in reason_str:
            conclusion = (
                "Cost budget exceeded during debate. No further LLM calls "
                "were made. Any available partial results are below."
            )
        else:
            conclusion = (
                "Judge call failed during debate. The following are "
                "structured critiques from individual reviewers without "
                "a final consensus judgment."
            )

        return ConsensusSchema(
            final_conclusion=conclusion,
            consensus_confidence=0.0,
            adopted_contributions={},
            rejected_positions=[],
            remaining_disagreements=[],
            disagreement_confirmation=f"Partial return due to {reason_str}",
            preserved_minority_opinions=[],
            partial_return=True,
            critiques_summary=critiques,
            debate_metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Cleanup loop
    # ------------------------------------------------------------------

    async def _cleanup_loop(self) -> None:
        """Periodically remove expired jobs from the task store."""
        while True:
            try:
                await asyncio.sleep(300)  # check every 5 minutes
                now = datetime.now(UTC)
                expired = [
                    jid
                    for jid, job in self._task_store.items()
                    if job.status in ("DONE", "FAILED", "CANCELLED")
                    and (now - job.updated_at).total_seconds() > _JOB_RETENTION_SECONDS
                ]
                for jid in expired:
                    del self._task_store[jid]
                    logger.debug("Cleaned up expired job: %s", jid)
                if expired:
                    logger.info("Cleaned up %d expired debate jobs", len(expired))
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in cleanup loop")
