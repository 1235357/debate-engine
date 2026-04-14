"""DebateEval Metrics -- 7 core evaluation metrics for benchmarking DebateEngine.

All metrics are designed to work without external API calls or heavy ML
dependencies.  Keyword-based matching is used for BDR/FAR; a production
deployment may swap in embedding-based similarity for higher accuracy.

Metrics:
    BDR  - Bug Discovery Rate
    FAR  - False Alarm Rate
    CV   - Consensus Validity
    CIS  - Conformity Impact Score
    CE   - Convergence Efficiency
    RD   - Reasoning Depth
    HD   - Hallucination Delta
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class MetricName(StrEnum):
    BDR = "bug_discovery_rate"
    FAR = "false_alarm_rate"
    CV = "consensus_validity"
    CIS = "conformity_impact_score"
    CE = "convergence_efficiency"
    RD = "reasoning_depth"
    HD = "hallucination_delta"


@dataclass
class MetricResult:
    name: MetricName
    value: float
    description: str
    details: dict = field(default_factory=dict)


class DebateEvalScores:
    def __init__(self) -> None:
        self.metrics: list[MetricResult] = []

    def add(self, metric: MetricResult) -> None:
        self.metrics.append(metric)

    def get(self, name: MetricName) -> MetricResult | None:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def to_dict(self) -> dict:
        return {
            m.name.value: {"value": m.value, "description": m.description, "details": m.details}
            for m in self.metrics
        }

    def summary(self) -> str:
        if not self.metrics:
            return "DebateEvalScores: (no metrics recorded)"
        lines = ["DebateEvalScores", "=" * 60]
        for m in self.metrics:
            lines.append(f"  {m.name.value:30s} = {m.value:.4f}")
            lines.append(f"    {m.description}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def __repr__(self) -> str:
        names = ", ".join(m.name.value for m in self.metrics)
        return f"DebateEvalScores([{names}])"


_STOP_WORDS: frozenset[str] = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in on at to for "
    "with by from as into through during before after above below "
    "between out off over under again further then once here there "
    "when where why how all both each few more most other some such "
    "no nor not only own same so than too very and but or if while "
    "it its this that these those i me my we our you your he him his "
    "she her they them their what which who whom".split()
)


def _tokenise(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def _keyword_overlap_score(a: str, b: str) -> float:
    tokens_a = _tokenise(a)
    tokens_b = _tokenise(b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _defect_match_score(discovered: dict, gold: dict, similarity_threshold: float = 0.75) -> float:
    d_desc = discovered.get("description", "")
    g_desc = gold.get("description", "")
    desc_score = _keyword_overlap_score(d_desc, g_desc)
    d_type = discovered.get("defect_type", "").upper()
    g_type = gold.get("defect_type", "").upper()
    if d_type != g_type:
        desc_score *= 0.3
    return desc_score


def compute_bdr(
    discovered_defects: list[dict], gold_standard: list[dict], similarity_threshold: float = 0.75
) -> MetricResult:
    if not gold_standard:
        return MetricResult(
            name=MetricName.BDR,
            value=1.0,
            description="BDR is 1.0 when there are no gold-standard defects.",
            details={"discovered_count": len(discovered_defects), "gold_count": 0},
        )
    matched_gold: set[int] = set()
    tp_count = 0
    for disc in discovered_defects:
        best_score, best_idx = 0.0, -1
        for gi, gold in enumerate(gold_standard):
            if gi in matched_gold:
                continue
            score = _defect_match_score(disc, gold)
            if score > best_score:
                best_score, best_idx = score, gi
        if best_score >= similarity_threshold and best_idx >= 0:
            tp_count += 1
            matched_gold.add(best_idx)
    bdr = tp_count / len(gold_standard)
    return MetricResult(
        name=MetricName.BDR,
        value=round(bdr, 4),
        description=f"Bug Discovery Rate: {tp_count}/{len(gold_standard)} gold defects discovered.",
        details={
            "true_positives": tp_count,
            "gold_count": len(gold_standard),
            "discovered_count": len(discovered_defects),
        },
    )


def compute_far(
    discovered_defects: list[dict], gold_standard: list[dict], similarity_threshold: float = 0.75
) -> MetricResult:
    if not discovered_defects:
        return MetricResult(
            name=MetricName.FAR,
            value=0.0,
            description="FAR is 0.0 when no defects were discovered.",
            details={"discovered_count": 0, "gold_count": len(gold_standard)},
        )
    matched_gold: set[int] = set()
    false_alarm_count = 0
    for disc in discovered_defects:
        best_score, best_idx = 0.0, -1
        for gi, gold in enumerate(gold_standard):
            if gi in matched_gold:
                continue
            score = _defect_match_score(disc, gold)
            if score > best_score:
                best_score, best_idx = score, gi
        if best_score >= similarity_threshold and best_idx >= 0:
            matched_gold.add(best_idx)
        else:
            false_alarm_count += 1
    far = false_alarm_count / len(discovered_defects)
    return MetricResult(
        name=MetricName.FAR,
        value=round(far, 4),
        description=f"False Alarm Rate: {false_alarm_count}/{len(discovered_defects)} discovered defects are false alarms.",
        details={
            "false_alarms": false_alarm_count,
            "discovered_count": len(discovered_defects),
            "gold_count": len(gold_standard),
        },
    )


def compute_cv(consensus_conclusion: str, reference_answer: str) -> MetricResult:
    score = _keyword_overlap_score(consensus_conclusion, reference_answer)
    return MetricResult(
        name=MetricName.CV,
        value=round(score, 4),
        description=f"Consensus Validity: {score:.2%} keyword overlap between consensus and reference answer.",
        details={
            "consensus_length": len(consensus_conclusion),
            "reference_length": len(reference_answer),
        },
    )


def compute_cis(revision_history: list[dict], critiques: list[dict]) -> MetricResult:
    """Compute Conformity Impact Score (CIS).

    CIS_approx = 1 - (adopted_high_severity_changes / total_stance_changes)
    CIS near 0.0 = low quality degradation (good).
    CIS near 1.0 = high quality degradation (bad).
    """
    if not revision_history:
        return MetricResult(
            name=MetricName.CIS,
            value=0.0,
            description="CIS is 0.0 when there is no revision history.",
            details={"revision_count": 0, "critique_count": len(critiques)},
        )
    critique_severities: dict[tuple[int, str], str] = {}
    for c in critiques:
        severity = c.get("severity", "MINOR").upper()
        target_role = c.get("target_role", "")
        critique_severities[(c.get("round", 0), target_role)] = severity
    total_stance_changes = 0
    adopted_high_severity_changes = 0
    for rev in revision_history:
        old_claim = rev.get("old_claim", "")
        new_claim = rev.get("new_claim", "")
        role = rev.get("role", "")
        round_num = rev.get("round", 0)
        adopted = rev.get("adopted", True)
        if not old_claim and not new_claim:
            continue
        stance_delta = 1.0 - _keyword_overlap_score(old_claim, new_claim)
        if stance_delta < 0.01:
            continue
        total_stance_changes += 1
        severity = critique_severities.get((round_num, role), "MINOR")
        if severity in ("CRITICAL", "MAJOR") and adopted:
            adopted_high_severity_changes += 1
    if total_stance_changes == 0:
        return MetricResult(
            name=MetricName.CIS,
            value=0.0,
            description="CIS is 0.0 when there are no meaningful stance changes.",
            details={"revision_count": len(revision_history), "critique_count": len(critiques)},
        )
    cis = 1.0 - (adopted_high_severity_changes / total_stance_changes)
    return MetricResult(
        name=MetricName.CIS,
        value=round(cis, 4),
        description=f"Conformity Impact Score: {cis:.4f} ({'low' if cis < 0.3 else 'moderate' if cis < 0.7 else 'high'} degradation from sycophantic stance changes).",
        details={
            "adopted_high_severity_changes": adopted_high_severity_changes,
            "total_stance_changes": total_stance_changes,
            "revision_count": len(revision_history),
            "critique_count": len(critiques),
        },
    )


def compute_ce(cv_score: float, rounds_completed: int, total_cost_usd: float) -> MetricResult:
    if rounds_completed <= 0:
        return MetricResult(
            name=MetricName.CE,
            value=0.0,
            description="CE is 0.0 when no rounds were completed.",
            details={"cv_score": cv_score, "rounds": 0, "cost_usd": total_cost_usd},
        )
    if total_cost_usd <= 0.0:
        ce = cv_score / rounds_completed
        return MetricResult(
            name=MetricName.CE,
            value=round(ce, 4),
            description=f"Convergence Efficiency: {ce:.4f} (cost was zero).",
            details={"cv_score": cv_score, "rounds": rounds_completed, "cost_usd": 0.0},
        )
    ce = cv_score / (rounds_completed * total_cost_usd)
    return MetricResult(
        name=MetricName.CE,
        value=round(ce, 4),
        description=f"Convergence Efficiency: {ce:.4f} (CV={cv_score:.4f}, rounds={rounds_completed}, cost=${total_cost_usd:.4f}).",
        details={"cv_score": cv_score, "rounds": rounds_completed, "cost_usd": total_cost_usd},
    )


def compute_rd(critiques: list[dict], adopted_count: int = 0) -> MetricResult:
    if not critiques:
        return MetricResult(
            name=MetricName.RD,
            value=0.0,
            description="RD is 0.0 when there are no critiques.",
            details={"total_critiques": 0},
        )
    concrete_count = sum(1 for c in critiques if c.get("fix_kind", "").upper() == "CONCRETE_FIX")
    total_count = len(critiques)
    concrete_ratio = concrete_count / total_count
    if adopted_count > 0 and concrete_count > 0:
        adoption_ratio = adopted_count / concrete_count
        rd = concrete_ratio * adoption_ratio
        desc = f"Reasoning Depth: {rd:.4f} (concrete_fix_ratio={concrete_ratio:.2%}, adoption_ratio={adoption_ratio:.2%})."
    else:
        rd = concrete_ratio
        desc = f"Reasoning Depth (concrete_fix only): {rd:.4f} ({concrete_count}/{total_count} critiques have concrete fixes)."
    return MetricResult(
        name=MetricName.RD,
        value=round(rd, 4),
        description=desc,
        details={
            "concrete_fix_count": concrete_count,
            "total_critiques": total_count,
            "concrete_fix_ratio": round(concrete_ratio, 4),
            "adopted_count": adopted_count,
        },
    )


def compute_hd(debate_faithfulness: float, baseline_faithfulness: float) -> MetricResult:
    hd = debate_faithfulness - baseline_faithfulness
    qualifier = "fewer" if hd > 0 else "more" if hd < 0 else "same"
    return MetricResult(
        name=MetricName.HD,
        value=round(hd, 4),
        description=f"Hallucination Delta: {hd:+.4f} (debate={debate_faithfulness:.4f}, baseline={baseline_faithfulness:.4f}, {qualifier} hallucinations than baseline).",
        details={
            "debate_faithfulness": debate_faithfulness,
            "baseline_faithfulness": baseline_faithfulness,
        },
    )
