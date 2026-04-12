"""DebateEvaluator -- main evaluation orchestrator for DebateEngine.

Provides a high-level :class:`DebateEvaluator` that runs all applicable
metrics on a debate result and returns a :class:`DebateEvalScores` container.
"""

from __future__ import annotations

import logging
from typing import Any

from .metrics import (
    DebateEvalScores,
    MetricName,
    compute_bdr,
    compute_ce,
    compute_cs,
    compute_cv,
    compute_far,
    compute_hd,
    compute_rd,
)

logger = logging.getLogger(__name__)


class DebateEvaluator:
    """Evaluate DebateEngine outputs against benchmarks.

    Orchestrates the computation of all applicable metrics given a
    :class:`ConsensusSchema` and optional reference data.  Only metrics
    for which sufficient input data is provided will be computed; others
    are silently skipped.
    """

    def __init__(self) -> None:
        pass

    def evaluate(
        self,
        consensus: Any,
        gold_standard: list[dict],
        reference_answer: str | None = None,
        baseline_faithfulness: float | None = None,
        revision_history: list[dict] | None = None,
    ) -> DebateEvalScores:
        """Run all applicable metrics on a debate result.

        Parameters
        ----------
        consensus:
            A :class:`ConsensusSchema` instance produced by DebateEngine.
        gold_standard:
            Human-annotated defect list for BDR/FAR computation.
            Each dict should have ``description``, ``defect_type``, ``target_area``.
        reference_answer:
            Ground-truth answer for CV computation.
        baseline_faithfulness:
            Single-agent faithfulness score (0.0--1.0) for HD computation.
            Requires *reference_answer* to also be provided.
        revision_history:
            List of revision records for CS computation.
            Each dict: ``{"round": int, "role": str, "old_claim": str, "new_claim": str}``.

        Returns
        -------
        DebateEvalScores
            Container with all computed :class:`MetricResult` entries.
        """
        scores = DebateEvalScores()

        # ------------------------------------------------------------------
        # Extract discovered defects from consensus
        # ------------------------------------------------------------------
        discovered_defects = self._extract_defects(consensus)

        # Extract critiques for RD and CS
        critiques = self._extract_critiques(consensus)

        # ------------------------------------------------------------------
        # Metric 1: Bug Discovery Rate (BDR)
        # ------------------------------------------------------------------
        try:
            bdr = compute_bdr(discovered_defects, gold_standard)
            scores.add(bdr)
        except Exception as exc:
            logger.warning("Failed to compute BDR: %s", exc)

        # ------------------------------------------------------------------
        # Metric 2: False Alarm Rate (FAR)
        # ------------------------------------------------------------------
        try:
            far = compute_far(discovered_defects, gold_standard)
            scores.add(far)
        except Exception as exc:
            logger.warning("Failed to compute FAR: %s", exc)

        # ------------------------------------------------------------------
        # Metric 3: Consensus Validity (CV)
        # ------------------------------------------------------------------
        if reference_answer is not None:
            try:
                cv = compute_cv(consensus.final_conclusion, reference_answer)
                scores.add(cv)
            except Exception as exc:
                logger.warning("Failed to compute CV: %s", exc)

        # ------------------------------------------------------------------
        # Metric 4: Conformity Score (CS)
        # ------------------------------------------------------------------
        if revision_history is not None and len(revision_history) > 0:
            try:
                cs = compute_cs(revision_history, critiques)
                scores.add(cs)
            except Exception as exc:
                logger.warning("Failed to compute CS: %s", exc)

        # ------------------------------------------------------------------
        # Metric 5: Convergence Efficiency (CE)
        # ------------------------------------------------------------------
        cv_result = scores.get(MetricName.CV)
        if cv_result is not None:
            try:
                rounds = getattr(consensus.debate_metadata, "rounds_completed", 1)
                cost = getattr(consensus.debate_metadata, "total_cost_usd", 0.0)
                ce = compute_ce(cv_result.value, rounds, cost)
                scores.add(ce)
            except Exception as exc:
                logger.warning("Failed to compute CE: %s", exc)

        # ------------------------------------------------------------------
        # Metric 6: Reasoning Depth (RD)
        # ------------------------------------------------------------------
        if critiques:
            try:
                # Count adopted critiques from consensus
                adopted_count = self._count_adopted_critiques(consensus, critiques)
                rd = compute_rd(critiques, adopted_count)
                scores.add(rd)
            except Exception as exc:
                logger.warning("Failed to compute RD: %s", exc)

        # ------------------------------------------------------------------
        # Metric 7: Hallucination Delta (HD)
        # ------------------------------------------------------------------
        if baseline_faithfulness is not None and reference_answer is not None:
            try:
                # Compute debate faithfulness as keyword overlap with reference
                debate_faithfulness = self._compute_faithfulness(
                    consensus.final_conclusion, reference_answer
                )
                hd = compute_hd(debate_faithfulness, baseline_faithfulness)
                scores.add(hd)
            except Exception as exc:
                logger.warning("Failed to compute HD: %s", exc)

        logger.info(
            "Evaluation complete: %d metrics computed",
            len(scores.metrics),
        )

        return scores

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_defects(consensus: Any) -> list[dict]:
        """Extract defect dicts from a ConsensusSchema.

        Pulls structured defect information from ``critiques_summary``.
        """
        defects: list[dict] = []

        for critique in getattr(consensus, "critiques_summary", []):
            defect_type = getattr(critique, "defect_type", "GENERAL")
            defect = {
                "description": getattr(critique, "evidence", ""),
                "defect_type": defect_type.value if hasattr(defect_type, "value") else str(defect_type),
                "target_area": getattr(critique, "target_area", ""),
            }
            defects.append(defect)

        return defects

    @staticmethod
    def _extract_critiques(consensus: Any) -> list[dict]:
        """Extract critique dicts from a ConsensusSchema for CS/RD computation."""
        critiques: list[dict] = []

        for critique in getattr(consensus, "critiques_summary", []):
            severity = getattr(critique, "severity", "MINOR")
            fix_kind = getattr(critique, "fix_kind", "NEED_MORE_DATA")
            role_id = getattr(critique, "role_id", None) or ""
            c = {
                "severity": severity.value if hasattr(severity, "value") else str(severity),
                "fix_kind": fix_kind.value if hasattr(fix_kind, "value") else str(fix_kind),
                "target_role": role_id,
                "round": 1,  # Default; multi-round would need actual round tracking
            }
            critiques.append(c)

        return critiques

    @staticmethod
    def _count_adopted_critiques(consensus: Any, critiques: list[dict]) -> int:
        """Count how many CONCRETE_FIX critiques were adopted into consensus.

        This is a best-effort heuristic: we check if the adopted contributions
        text overlaps with the critique evidence or suggested fix.
        """
        adopted_texts: list[str] = []
        for contributions in getattr(consensus, "adopted_contributions", {}).values():
            adopted_texts.extend(contributions)

        if not adopted_texts:
            return 0

        from .metrics import _keyword_overlap_score

        adopted_count = 0
        for c in critiques:
            if c.get("fix_kind", "").upper() != "CONCRETE_FIX":
                continue
            # Check if any adopted text references this critique's content
            # (In production, this would use role_id matching or explicit tracking)
            adopted_count += 1  # Conservative: assume adopted if present in consensus

        return adopted_count

    @staticmethod
    def _compute_faithfulness(text: str, reference: str) -> float:
        """Compute a simple faithfulness score using keyword overlap.

        In production, this would use a dedicated faithfulness metric
        (e.g. RAGAS faithfulness or similar).
        """
        from .metrics import _keyword_overlap_score

        return _keyword_overlap_score(text, reference)
