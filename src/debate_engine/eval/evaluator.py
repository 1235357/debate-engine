"""DebateEvaluator -- main evaluation orchestrator for DebateEngine."""

from __future__ import annotations
import logging
from typing import Any
from .metrics import (
    DebateEvalScores, MetricName,
    compute_bdr, compute_ce, compute_cis, compute_cv,
    compute_far, compute_hd, compute_rd,
)

logger = logging.getLogger(__name__)


class DebateEvaluator:
    """Evaluate DebateEngine outputs against benchmarks."""

    def __init__(self) -> None:
        pass

    def evaluate(self, consensus: Any, gold_standard: list[dict],
                 reference_answer: str | None = None,
                 baseline_faithfulness: float | None = None,
                 revision_history: list[dict] | None = None) -> DebateEvalScores:
        scores = DebateEvalScores()
        discovered_defects = self._extract_defects(consensus)
        critiques = self._extract_critiques(consensus)

        try:
            scores.add(compute_bdr(discovered_defects, gold_standard))
        except Exception as exc:
            logger.warning("Failed to compute BDR: %s", exc)
        try:
            scores.add(compute_far(discovered_defects, gold_standard))
        except Exception as exc:
            logger.warning("Failed to compute FAR: %s", exc)
        if reference_answer is not None:
            try:
                scores.add(compute_cv(consensus.final_conclusion, reference_answer))
            except Exception as exc:
                logger.warning("Failed to compute CV: %s", exc)
        if revision_history is not None and len(revision_history) > 0:
            try:
                scores.add(compute_cis(revision_history, critiques))
            except Exception as exc:
                logger.warning("Failed to compute CIS: %s", exc)
        cv_result = scores.get(MetricName.CV)
        if cv_result is not None:
            try:
                rounds = getattr(consensus.debate_metadata, "rounds_completed", 1)
                cost = getattr(consensus.debate_metadata, "total_cost_usd", 0.0)
                scores.add(compute_ce(cv_result.value, rounds, cost))
            except Exception as exc:
                logger.warning("Failed to compute CE: %s", exc)
        if critiques:
            try:
                adopted_count = self._count_adopted_critiques(consensus, critiques)
                scores.add(compute_rd(critiques, adopted_count))
            except Exception as exc:
                logger.warning("Failed to compute RD: %s", exc)
        if baseline_faithfulness is not None and reference_answer is not None:
            try:
                debate_faithfulness = self._compute_faithfulness(consensus.final_conclusion, reference_answer)
                scores.add(compute_hd(debate_faithfulness, baseline_faithfulness))
            except Exception as exc:
                logger.warning("Failed to compute HD: %s", exc)
        logger.info("Evaluation complete: %d metrics computed", len(scores.metrics))
        return scores

    @staticmethod
    def _extract_defects(consensus: Any) -> list[dict]:
        defects = []
        for critique in getattr(consensus, "critiques_summary", []):
            defect_type = getattr(critique, "defect_type", "GENERAL")
            defects.append({"description": getattr(critique, "evidence", ""), "defect_type": defect_type.value if hasattr(defect_type, "value") else str(defect_type), "target_area": getattr(critique, "target_area", "")})
        return defects

    @staticmethod
    def _extract_critiques(consensus: Any) -> list[dict]:
        critiques = []
        for critique in getattr(consensus, "critiques_summary", []):
            severity = getattr(critique, "severity", "MINOR")
            fix_kind = getattr(critique, "fix_kind", "NEED_MORE_DATA")
            role_id = getattr(critique, "role_id", None) or ""
            critiques.append({"severity": severity.value if hasattr(severity, "value") else str(severity), "fix_kind": fix_kind.value if hasattr(fix_kind, "value") else str(fix_kind), "target_role": role_id, "round": 1})
        return critiques

    @staticmethod
    def _count_adopted_critiques(consensus: Any, critiques: list[dict]) -> int:
        adopted_texts = []
        for contributions in getattr(consensus, "adopted_contributions", {}).values():
            adopted_texts.extend(contributions)
        if not adopted_texts:
            return 0
        adopted_count = 0
        for c in critiques:
            if c.get("fix_kind", "").upper() != "CONCRETE_FIX":
                continue
            adopted_count += 1
        return adopted_count

    @staticmethod
    def _compute_faithfulness(text: str, reference: str) -> float:
        from .metrics import _keyword_overlap_score
        return _keyword_overlap_score(text, reference)