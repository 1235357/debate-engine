"""QuickCritiqueEngine -- the v0.1 synchronous critique pipeline.

Executes a single round of multi-role structured critique:
  Phase 0: Route task type, load role templates
  Phase 1: Concurrent critique generation (asyncio.gather, 3 roles)
  Phase 2: Anonymize critiques
  Phase 3: Quorum check
  Phase 4: Judge summarization (if quorum met)
  Phase 5: Format result, log, return ConsensusSchema
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from ..api.key_manager import APIKeyManager
from ..providers.config import ProviderConfig
from ..providers.llm_provider import CallResult, LLMProvider
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
# Task type auto-detection (keyword matching)
# ---------------------------------------------------------------------------

_TASK_TYPE_KEYWORDS: dict[str, list[str]] = {
    "CODE_REVIEW": [
        "function", "class ", "def ", "import ", "code", "bug",
        "sql", "query", "api", "endpoint", "repository", "module",
        "refactor", "test", "pytest", "unittest", "async def",
    ],
    "RAG_VALIDATION": [
        "context", "retrieval", "document", "source", "reference",
        "hallucin", "grounding", "rag", "embedding", "vector",
        "chunk", "passage", "citation",
    ],
    "ARCHITECTURE_DECISION": [
        "architect", "microservice", "monolith", "scalab", "design pattern",
        "infrastructure", "deploy", "kubernetes", "docker", "event-driven",
        "cqrs", "event sourcing", "service mesh", "load balanc",
    ],
}


def _auto_detect_task_type(content: str) -> str:
    """Simple keyword-based task type detection.

    Returns the task type string with the highest keyword hit count, or
    ``"GENERAL_CRITIQUE"`` if no type scores above the threshold.
    """
    content_lower = content.lower()
    scores: dict[str, int] = {}
    for task_type, keywords in _TASK_TYPE_KEYWORDS.items():
        scores[task_type] = sum(1 for kw in keywords if kw in content_lower)
    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best_type] < 2:
        return "GENERAL_CRITIQUE"
    return best_type


def _resolve_task_type(raw: Any) -> str:
    """Normalize task_type to a plain string regardless of input type.

    Handles both ``TaskType`` enum members and raw strings.
    """
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw)


def _resolve_provider_mode(config: ProviderConfig) -> str:
    """Return the provider mode as a string matching the schema enum."""
    return config.mode.value


# ---------------------------------------------------------------------------
# QuickCritiqueEngine
# ---------------------------------------------------------------------------


class QuickCritiqueEngine:
    """v0.1 synchronous (async-capable) critique engine.

    Executes a single round of multi-role structured critique and returns a
    :class:`ConsensusSchema` (imported from ``debate_engine.schemas``).

    Parameters
    ----------
    provider_config:
        Provider configuration.  When ``None``, :meth:`ProviderConfig.from_env`
        is used to read settings from environment variables.
    """

    def __init__(self, provider_config: ProviderConfig | None = None, key_manager: APIKeyManager | None = None) -> None:
        self.provider = LLMProvider(provider_config or ProviderConfig.from_env(), key_manager=key_manager)

    async def critique(self, config: Any) -> Any:
        """Run the full quick_critique pipeline.

        Parameters
        ----------
        config:
            A ``CritiqueConfigSchema`` instance from ``debate_engine.schemas``.

        Returns
        -------
        ConsensusSchema
            The consensus result.  May be a partial return if quorum or judge
            fails (``partial_return=True``).
        """
        # Lazy import to avoid hard dependency at module level
        from debate_engine.schemas import (
            ConsensusSchema,
            CritiqueSchema,
            DebateMetadata,
            TerminationReason,
        )
        from debate_engine.schemas import (
            ProviderMode as SchemaProviderMode,
        )
        from debate_engine.schemas import (
            TaskType as SchemaTaskType,
        )

        request_id = generate_request_id()
        start_time = time.monotonic()
        logger.info("quick_critique started request_id=%s", request_id)

        # ------------------------------------------------------------------
        # Phase 0: Route task type, load role templates
        # ------------------------------------------------------------------
        raw_task_type = config.task_type
        task_type_str = _resolve_task_type(raw_task_type)

        if task_type_str == "AUTO":
            task_type_str = _auto_detect_task_type(config.content)
            logger.info("Auto-detected task_type=%s", task_type_str)

        # Map to schema enum
        try:
            task_type_enum = SchemaTaskType(task_type_str)
        except ValueError:
            task_type_enum = SchemaTaskType.GENERAL_CRITIQUE

        provider_mode_str = _resolve_provider_mode(self.provider.config)
        try:
            provider_mode_enum = SchemaProviderMode(provider_mode_str)
        except ValueError:
            provider_mode_enum = SchemaProviderMode.STABLE

        enable_da = getattr(config, "enable_devil_advocate", True)
        cost_budget = getattr(config, "cost_budget_usd", 0.30)
        custom_prompts = getattr(config, "custom_role_prompts", None) or {}

        roles = ["ROLE_A", "ROLE_B", "DA_ROLE"] if enable_da else ["ROLE_A", "ROLE_B", "ROLE_C"]
        role_types = ["critic_a", "critic_b", "devil_advocate"] if enable_da else ["critic_a", "critic_b", "critic_c"]

        # ------------------------------------------------------------------
        # Phase 1: Concurrent critique generation
        # ------------------------------------------------------------------
        async def _run_role(role: str, role_type: str) -> tuple[Any, CallResult]:
            system_prompt = build_role_system_prompt(
                role_type=role,
                task_type=task_type_str,
                custom_prompt=custom_prompts.get(role),
            )
            user_message = {
                "role": "user",
                "content": (
                    f"Please critique the following content. Output a valid "
                    f"JSON object matching the CritiqueSchema.\n\n"
                    f"--- Content to critique ---\n{config.content}\n"
                    f"--- End of content ---"
                ),
            }
            return await self.provider.call(
                messages=[user_message],
                system_prompt=system_prompt,
                response_model=CritiqueSchema,
                role_type=role_type,
                temperature=0.3,
            )

        # Check cost budget before launching roles
        if self.provider.cost_accumulated >= cost_budget:
            logger.warning(
                "Cost budget exceeded before critique start: "
                "%.4f >= %.4f",
                self.provider.cost_accumulated,
                cost_budget,
            )
            return self._build_budget_exceeded_result(
                request_id=request_id,
                task_type_enum=task_type_enum,
                provider_mode_enum=provider_mode_enum,
                start_time=start_time,
                cost_budget=cost_budget,
            )

        try:
            role_results = await asyncio.gather(
                *[_run_role(r, rt) for r, rt in zip(roles, role_types)],
                return_exceptions=True,
            )
        except Exception as exc:
            logger.error("Unexpected error in critique gather: %s", exc)
            role_results = [exc] * len(roles)

        # Collect results, separating successes from failures
        critiques: list[Any] = []
        call_results: list[CallResult] = []
        models_used: set[str] = set()
        total_parse_attempts = 0

        for idx, result in enumerate(role_results):
            if isinstance(result, Exception):
                logger.error("Role %s raised exception: %s", roles[idx], result)
                call_results.append(
                    CallResult(
                        status="ROLE_FAILED",
                        error_message=str(result),
                        model_used="unknown",
                    )
                )
                continue

            parsed, call_result = result
            call_results.append(call_result)
            total_parse_attempts += call_result.parse_attempts
            if call_result.model_used:
                models_used.add(call_result.model_used)

            if call_result.status == "SUCCESS" and parsed is not None:
                # Ensure role_id is set
                if hasattr(parsed, "role_id"):
                    if not parsed.role_id:
                        parsed = parsed.model_copy(update={"role_id": roles[idx]})
                critiques.append(parsed)
            elif call_result.status == "PARSE_FAILED" and parsed is not None:
                # Degraded critique with defaults
                if hasattr(parsed, "role_id"):
                    parsed = parsed.model_copy(update={"role_id": roles[idx]})
                critiques.append(parsed)
            else:
                logger.warning(
                    "Role %s failed: status=%s error=%s",
                    roles[idx],
                    call_result.status,
                    call_result.error_message,
                )

        # Check cost budget after role generation
        if self.provider.cost_accumulated >= cost_budget:
            logger.warning("Cost budget exceeded after role generation")
            return self._build_budget_exceeded_result(
                request_id=request_id,
                task_type_enum=task_type_enum,
                provider_mode_enum=provider_mode_enum,
                start_time=start_time,
                cost_budget=cost_budget,
                critiques=critiques,
                call_results=call_results,
                models_used=models_used,
                total_parse_attempts=total_parse_attempts,
            )

        # ------------------------------------------------------------------
        # Phase 2: Anonymize critiques
        # ------------------------------------------------------------------
        anonymized = anonymize_critiques(critiques)

        # ------------------------------------------------------------------
        # Phase 3: Quorum check
        # ------------------------------------------------------------------
        quorum_met, success_count = check_quorum(call_results)
        logger.info(
            "Quorum check: met=%s success_count=%d", quorum_met, success_count
        )

        if not quorum_met:
            logger.warning("Quorum not met; returning partial result")
            return self._build_partial_result(
                request_id=request_id,
                task_type_enum=task_type_enum,
                provider_mode_enum=provider_mode_enum,
                start_time=start_time,
                critiques=anonymized,
                call_results=call_results,
                models_used=models_used,
                total_parse_attempts=total_parse_attempts,
                termination_reason=TerminationReason.QUORUM_FAILED,
            )

        # ------------------------------------------------------------------
        # Phase 4: Judge summarization
        # ------------------------------------------------------------------
        judge_summary = build_judge_summary(anonymized, (quorum_met, success_count))
        judge_messages = [
            {"role": "user", "content": judge_summary},
        ]

        judge_parsed, judge_result = await self.provider.call(
            messages=judge_messages,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            response_model=ConsensusSchema,
            role_type="judge",
            temperature=0.2,
        )

        total_parse_attempts += judge_result.parse_attempts
        if judge_result.model_used:
            models_used.add(judge_result.model_used)

        if judge_result.status != "SUCCESS" or judge_parsed is None:
            logger.error(
                "Judge failed: status=%s error=%s",
                judge_result.status,
                judge_result.error_message,
            )
            return self._build_partial_result(
                request_id=request_id,
                task_type_enum=task_type_enum,
                provider_mode_enum=provider_mode_enum,
                start_time=start_time,
                critiques=anonymized,
                call_results=call_results,
                models_used=models_used,
                total_parse_attempts=total_parse_attempts,
                termination_reason=TerminationReason.JUDGE_FAILED,
            )

        # ------------------------------------------------------------------
        # Phase 5: Format result, log, return
        # ------------------------------------------------------------------
        total_latency_ms = (time.monotonic() - start_time) * 1000
        total_cost = self.provider.cost_accumulated

        # Enrich metadata
        metadata = DebateMetadata(
            request_id=request_id,
            job_id=None,
            task_type=task_type_enum,
            provider_mode=provider_mode_enum,
            rounds_completed=1,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(total_latency_ms, 1),
            models_used=list(models_used),
            quorum_achieved=quorum_met,
            termination_reason=TerminationReason.COMPLETED,
            parse_attempts_total=total_parse_attempts,
        )

        # Enrich consensus with metadata and critiques
        final = judge_parsed.model_copy(
            update={
                "debate_metadata": metadata,
                "critiques_summary": anonymized,
                "partial_return": False,
            }
        )

        # Cap consensus_confidence at 0.95 (defense in depth)
        if hasattr(final, "consensus_confidence") and final.consensus_confidence > 0.95:
            final = final.model_copy(update={"consensus_confidence": 0.95})

        logger.info(
            "quick_critique completed request_id=%s cost=%.6f latency=%.0fms "
            "quorum=%s termination=%s",
            request_id,
            total_cost,
            total_latency_ms,
            quorum_met,
            "COMPLETED",
        )

        return final

    # ------------------------------------------------------------------
    # Partial / budget-exceeded result builders
    # ------------------------------------------------------------------

    def _build_partial_result(
        self,
        *,
        request_id: str,
        task_type_enum: Any,
        provider_mode_enum: Any,
        start_time: float,
        critiques: list[Any],
        call_results: list[CallResult],
        models_used: set[str],
        total_parse_attempts: int,
        termination_reason: Any,
    ) -> Any:
        """Build a partial ConsensusSchema when quorum or judge fails."""
        from debate_engine.schemas import (
            ConsensusSchema,
            DebateMetadata,
        )

        total_latency_ms = (time.monotonic() - start_time) * 1000
        total_cost = self.provider.cost_accumulated

        metadata = DebateMetadata(
            request_id=request_id,
            job_id=None,
            task_type=task_type_enum,
            provider_mode=provider_mode_enum,
            rounds_completed=1,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(total_latency_ms, 1),
            models_used=list(models_used),
            quorum_achieved=False,
            termination_reason=termination_reason,
            parse_attempts_total=total_parse_attempts,
        )

        reason_str = str(termination_reason.value) if hasattr(termination_reason, "value") else str(termination_reason)

        if "QUORUM" in reason_str:
            conclusion = (
                "Quorum not met (fewer than 2 of 3 reviewers returned "
                "successfully). The following partial critique results are "
                "provided for reference but should not be treated as a "
                "reliable consensus."
            )
        else:
            conclusion = (
                "Judge call failed. The following are structured critiques "
                "from individual reviewers, but they have not been "
                "synthesized into a final consensus judgment."
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

    def _build_budget_exceeded_result(
        self,
        *,
        request_id: str,
        task_type_enum: Any,
        provider_mode_enum: Any,
        start_time: float,
        cost_budget: float,
        critiques: list[Any] | None = None,
        call_results: list[CallResult] | None = None,
        models_used: set[str] | None = None,
        total_parse_attempts: int = 0,
    ) -> Any:
        """Build a partial ConsensusSchema when cost budget is exceeded."""
        from debate_engine.schemas import (
            ConsensusSchema,
            DebateMetadata,
            TerminationReason,
        )

        total_latency_ms = (time.monotonic() - start_time) * 1000
        total_cost = self.provider.cost_accumulated

        metadata = DebateMetadata(
            request_id=request_id,
            job_id=None,
            task_type=task_type_enum,
            provider_mode=provider_mode_enum,
            rounds_completed=1,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(total_latency_ms, 1),
            models_used=list(models_used or set()),
            quorum_achieved=False,
            termination_reason=TerminationReason.COST_BUDGET_EXCEEDED,
            parse_attempts_total=total_parse_attempts,
        )

        has_critiques = bool(critiques)
        return ConsensusSchema(
            final_conclusion=(
                f"Cost budget exceeded (${total_cost:.4f} >= ${cost_budget:.4f}). "
                "No further LLM calls were made. Any available partial "
                "critique results are provided below."
            ),
            consensus_confidence=0.0,
            adopted_contributions={},
            rejected_positions=[],
            remaining_disagreements=[],
            disagreement_confirmation="Cost budget exceeded before completion",
            preserved_minority_opinions=[],
            partial_return=has_critiques,
            critiques_summary=critiques or [],
            debate_metadata=metadata,
        )
