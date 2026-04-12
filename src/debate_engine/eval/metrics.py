"""DebateEval Metrics -- 7 core evaluation metrics for benchmarking DebateEngine.

All metrics are designed to work without external API calls or heavy ML
dependencies.  Keyword-based matching is used for BDR/FAR; a production
deployment may swap in embedding-based similarity for higher accuracy.

Metrics:
    BDR  - Bug Discovery Rate
    FAR  - False Alarm Rate
    CV   - Consensus Validity
    CS   - Conformity Score (original metric)
    CE   - Convergence Efficiency
    RD   - Reasoning Depth
    HD   - Hallucination Delta
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enum & data containers
# ---------------------------------------------------------------------------


class MetricName(str, Enum):
    """Canonical identifiers for each DebateEval metric."""

    BDR = "bug_discovery_rate"
    FAR = "false_alarm_rate"
    CV = "consensus_validity"
    CS = "conformity_score"
    CE = "convergence_efficiency"
    RD = "reasoning_depth"
    HD = "hallucination_delta"


@dataclass
class MetricResult:
    """A single metric computation result.

    Attributes:
        name: Which metric was computed.
        value: Numeric score (interpretation varies by metric).
        description: Human-readable explanation of this particular result.
        details: Optional structured metadata for further analysis.
    """

    name: MetricName
    value: float
    description: str
    details: dict = field(default_factory=dict)


class DebateEvalScores:
    """Container for all evaluation scores produced in a single evaluation run.

    Provides dict-like access, serialisation helpers, and a human-readable
    summary.
    """

    def __init__(self) -> None:
        self.metrics: list[MetricResult] = []

    # -- mutators -----------------------------------------------------------

    def add(self, metric: MetricResult) -> None:
        """Append a metric result to the collection."""
        self.metrics.append(metric)

    # -- accessors ----------------------------------------------------------

    def get(self, name: MetricName) -> MetricResult | None:
        """Return the first ``MetricResult`` matching *name*, or ``None``."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise all scores to a plain ``dict``.

        Returns:
            ``{"metric_name": {"value": float, "description": str, ...}, ...}``
        """
        return {
            m.name.value: {
                "value": m.value,
                "description": m.description,
                "details": m.details,
            }
            for m in self.metrics
        }

    def summary(self) -> str:
        """Return a human-readable multi-line summary of all scores."""
        if not self.metrics:
            return "DebateEvalScores: (no metrics recorded)"
        lines = ["DebateEvalScores"]
        lines.append("=" * 60)
        for m in self.metrics:
            lines.append(f"  {m.name.value:30s} = {m.value:.4f}")
            lines.append(f"    {m.description}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def __repr__(self) -> str:
        names = ", ".join(m.name.value for m in self.metrics)
        return f"DebateEvalScores([{names}])"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
    """Lowercase, strip punctuation, remove stop-words, return set of tokens."""
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def _keyword_overlap_score(a: str, b: str) -> float:
    """Jaccard-like similarity on significant tokens.

    Returns a value between 0.0 and 1.0.
    """
    tokens_a = _tokenise(a)
    tokens_b = _tokenise(b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _defect_match_score(
    discovered: dict,
    gold: dict,
    similarity_threshold: float = 0.75,
) -> float:
    """Return the similarity score between a discovered defect and a gold defect.

    Matching is primarily based on the ``description`` field using keyword
    Jaccard overlap.  ``defect_type`` must match exactly (case-insensitive)
    for the description score to be considered -- if types differ, the score
    is halved to penalise type mismatches.
    """
    d_desc = discovered.get("description", "")
    g_desc = gold.get("description", "")
    desc_score = _keyword_overlap_score(d_desc, g_desc)

    # Penalise if defect types don't match
    d_type = discovered.get("defect_type", "").upper()
    g_type = gold.get("defect_type", "").upper()
    type_matches = d_type == g_type

    if not type_matches:
        desc_score *= 0.3  # Significant penalty for type mismatch

    return desc_score


# ---------------------------------------------------------------------------
# Metric 1: Bug Discovery Rate (BDR)
# ---------------------------------------------------------------------------


def compute_bdr(
    discovered_defects: list[dict],
    gold_standard: list[dict],
    similarity_threshold: float = 0.75,
) -> MetricResult:
    """Compute Bug Discovery Rate.

    ``BDR = |discovered ∩ gold| / |gold|``

    Each defect dict should contain at least ``description``, ``defect_type``,
    and ``target_area`` keys.  Matching is keyword-overlap-based; a discovered
    defect is counted as a true positive if its best match against any gold
    defect meets *similarity_threshold*.

    Parameters
    ----------
    discovered_defects:
        Defects found by the DebateEngine.
    gold_standard:
        Human-annotated reference defects.
    similarity_threshold:
        Minimum overlap score to count a match (default 0.75).

    Returns
    -------
    MetricResult with ``name=MetricName.BDR`` and value in [0.0, 1.0].
    """
    if not gold_standard:
        return MetricResult(
            name=MetricName.BDR,
            value=1.0,
            description="BDR is 1.0 when there are no gold-standard defects (vacuously true).",
            details={"discovered_count": len(discovered_defects), "gold_count": 0},
        )

    matched_gold: set[int] = set()
    tp_count = 0

    for disc in discovered_defects:
        best_score = 0.0
        best_gold_idx = -1
        for gi, gold in enumerate(gold_standard):
            if gi in matched_gold:
                continue
            score = _defect_match_score(disc, gold)
            if score > best_score:
                best_score = score
                best_gold_idx = gi
        if best_score >= similarity_threshold and best_gold_idx >= 0:
            tp_count += 1
            matched_gold.add(best_gold_idx)

    bdr = tp_count / len(gold_standard)

    return MetricResult(
        name=MetricName.BDR,
        value=round(bdr, 4),
        description=(
            f"Bug Discovery Rate: {tp_count}/{len(gold_standard)} gold defects "
            f"discovered (threshold={similarity_threshold})."
        ),
        details={
            "true_positives": tp_count,
            "gold_count": len(gold_standard),
            "discovered_count": len(discovered_defects),
            "similarity_threshold": similarity_threshold,
        },
    )


# ---------------------------------------------------------------------------
# Metric 2: False Alarm Rate (FAR)
# ---------------------------------------------------------------------------


def compute_far(
    discovered_defects: list[dict],
    gold_standard: list[dict],
    similarity_threshold: float = 0.75,
) -> MetricResult:
    """Compute False Alarm Rate.

    ``FAR = |discovered - gold| / |discovered|``

    A discovered defect is a false alarm if it does not match any gold
    standard defect above *similarity_threshold*.

    Parameters
    ----------
    discovered_defects:
        Defects found by the DebateEngine.
    gold_standard:
        Human-annotated reference defects.
    similarity_threshold:
        Minimum overlap score to count a match (default 0.75).

    Returns
    -------
    MetricResult with ``name=MetricName.FAR`` and value in [0.0, 1.0].
    Lower is better.
    """
    if not discovered_defects:
        return MetricResult(
            name=MetricName.FAR,
            value=0.0,
            description="FAR is 0.0 when no defects were discovered (no false alarms possible).",
            details={"discovered_count": 0, "gold_count": len(gold_standard)},
        )

    matched_gold: set[int] = set()
    false_alarm_count = 0

    for disc in discovered_defects:
        best_score = 0.0
        best_gold_idx = -1
        for gi, gold in enumerate(gold_standard):
            if gi in matched_gold:
                continue
            score = _defect_match_score(disc, gold)
            if score > best_score:
                best_score = score
                best_gold_idx = gi
        if best_score >= similarity_threshold and best_gold_idx >= 0:
            matched_gold.add(best_gold_idx)
        else:
            false_alarm_count += 1

    far = false_alarm_count / len(discovered_defects)

    return MetricResult(
        name=MetricName.FAR,
        value=round(far, 4),
        description=(
            f"False Alarm Rate: {false_alarm_count}/{len(discovered_defects)} "
            f"discovered defects are false alarms (threshold={similarity_threshold})."
        ),
        details={
            "false_alarms": false_alarm_count,
            "discovered_count": len(discovered_defects),
            "gold_count": len(gold_standard),
            "similarity_threshold": similarity_threshold,
        },
    )


# ---------------------------------------------------------------------------
# Metric 3: Consensus Validity (CV)
# ---------------------------------------------------------------------------


def compute_cv(
    consensus_conclusion: str,
    reference_answer: str,
) -> MetricResult:
    """Compute Consensus Validity.

    Keyword-based Jaccard similarity between the consensus conclusion and a
    reference answer.  Returns a value between 0.0 and 1.0.

    Parameters
    ----------
    consensus_conclusion:
        The ``final_conclusion`` from a :class:`ConsensusSchema`.
    reference_answer:
        The ground-truth or expert-provided reference answer.

    Returns
    -------
    MetricResult with ``name=MetricName.CV`` and value in [0.0, 1.0].
    """
    score = _keyword_overlap_score(consensus_conclusion, reference_answer)

    return MetricResult(
        name=MetricName.CV,
        value=round(score, 4),
        description=(
            f"Consensus Validity: {score:.2%} keyword overlap between "
            f"consensus and reference answer."
        ),
        details={
            "consensus_length": len(consensus_conclusion),
            "reference_length": len(reference_answer),
        },
    )


# ---------------------------------------------------------------------------
# Metric 4: Conformity Score (CS) -- ORIGINAL METRIC
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 1.0,
    "MAJOR": 0.6,
    "MINOR": 0.2,
}


def compute_cs(
    revision_history: list[dict],
    critiques: list[dict],
) -> MetricResult:
    """Compute Conformity Score (original metric).

    Measures whether stance changes are *proportional* to critique severity.
    A high score means agents changed their claims more in response to
    severe critiques (evidence-driven).  A low score means agents changed
    claims regardless of severity (sycophantic).

    ``CS = 1 - mean(|stance_delta_i - severity_weight_i|)``

    where ``stance_delta_i`` is normalised to [0, 1] and ``severity_weight_i``
    is the critique weight (CRITICAL=1.0, MAJOR=0.6, MINOR=0.2).

    Interpretation:
        - CS near 1.0 = stance changes match severity (evidence-driven, good).
        - CS near 0.0 = stance changes ignore severity (sycophantic, bad).

    Parameters
    ----------
    revision_history:
        List of revision records, each with ``round``, ``role``,
        ``old_claim``, ``new_claim``.
    critiques:
        List of critique records, each with ``severity`` and ``target_role``.

    Returns
    -------
    MetricResult with ``name=MetricName.CS`` and value in [0.0, 1.0].
    """
    if not revision_history:
        return MetricResult(
            name=MetricName.CS,
            value=0.0,
            description="CS is 0.0 when there is no revision history.",
            details={"revision_count": 0, "critique_count": len(critiques)},
        )

    # Build a lookup from (round, role) -> severity weight
    critique_weights: dict[tuple[int, str], float] = {}
    for c in critiques:
        severity = c.get("severity", "MINOR").upper()
        weight = _SEVERITY_WEIGHTS.get(severity, 0.2)
        target_role = c.get("target_role", "")
        critique_weights[(c.get("round", 0), target_role)] = weight

    deviations: list[float] = []

    for rev in revision_history:
        old_claim = rev.get("old_claim", "")
        new_claim = rev.get("new_claim", "")
        role = rev.get("role", "")
        round_num = rev.get("round", 0)

        # stance_delta: 1 - Jaccard similarity (0 = no change, 1 = complete change)
        if not old_claim and not new_claim:
            stance_delta = 0.0
        else:
            stance_delta = 1.0 - _keyword_overlap_score(old_claim, new_claim)

        # Look up the severity weight for this revision
        weight = critique_weights.get((round_num, role), 0.2)  # default MINOR

        # Deviation: how far is the stance change from the expected severity?
        deviation = abs(stance_delta - weight)
        deviations.append(deviation)

    if not deviations:
        cs = 0.0
    else:
        mean_deviation = sum(deviations) / len(deviations)
        cs = max(0.0, 1.0 - mean_deviation)

    return MetricResult(
        name=MetricName.CS,
        value=round(cs, 4),
        description=(
            f"Conformity Score: {cs:.4f} "
            f"({'evidence-driven' if cs >= 0.7 else 'sycophantic' if cs < 0.3 else 'moderate'} "
            f"stance changes)."
        ),
        details={
            "mean_deviation": round(sum(deviations) / len(deviations), 4) if deviations else 0.0,
            "revision_count": len(revision_history),
            "critique_count": len(critiques),
        },
    )


# ---------------------------------------------------------------------------
# Metric 5: Convergence Efficiency (CE)
# ---------------------------------------------------------------------------


def compute_ce(
    cv_score: float,
    rounds_completed: int,
    total_cost_usd: float,
) -> MetricResult:
    """Compute Convergence Efficiency.

    ``CE = CV / (rounds * cost)``

    Higher is better.  Measures how much consensus validity is achieved
    per unit of computational resource (rounds and cost).

    Parameters
    ----------
    cv_score:
        The Consensus Validity score (0.0--1.0).
    rounds_completed:
        Number of debate rounds that ran.
    total_cost_usd:
        Total LLM API cost in USD.

    Returns
    -------
    MetricResult with ``name=MetricName.CE``.
    """
    if rounds_completed <= 0:
        return MetricResult(
            name=MetricName.CE,
            value=0.0,
            description="CE is 0.0 when no rounds were completed.",
            details={"cv_score": cv_score, "rounds": 0, "cost_usd": total_cost_usd},
        )

    if total_cost_usd <= 0.0:
        # Avoid division by zero; treat zero-cost as ideal (infinite efficiency)
        # but cap at a reasonable value
        ce = cv_score / rounds_completed
        return MetricResult(
            name=MetricName.CE,
            value=round(ce, 4),
            description=(
                f"Convergence Efficiency: {ce:.4f} (cost was zero, "
                f"using rounds-only denominator)."
            ),
            details={"cv_score": cv_score, "rounds": rounds_completed, "cost_usd": 0.0},
        )

    ce = cv_score / (rounds_completed * total_cost_usd)

    return MetricResult(
        name=MetricName.CE,
        value=round(ce, 4),
        description=(
            f"Convergence Efficiency: {ce:.4f} "
            f"(CV={cv_score:.4f}, rounds={rounds_completed}, cost=${total_cost_usd:.4f})."
        ),
        details={
            "cv_score": cv_score,
            "rounds": rounds_completed,
            "cost_usd": total_cost_usd,
        },
    )


# ---------------------------------------------------------------------------
# Metric 6: Reasoning Depth (RD)
# ---------------------------------------------------------------------------


def compute_rd(
    critiques: list[dict],
    adopted_count: int = 0,
) -> MetricResult:
    """Compute Reasoning Depth.

    ``RD = (CONCRETE_FIX ratio) * (adoption ratio)``

    The first factor measures what fraction of critiques provide concrete
    fixes (vs. validation steps or needs-more-data).  The second factor
    measures what fraction of concrete-fix critiques were actually adopted.
    If no adoption data is available, only the CONCRETE_FIX ratio is reported.

    Parameters
    ----------
    critiques:
        List of critique dicts, each with a ``fix_kind`` field.
    adopted_count:
        Number of CONCRETE_FIX critiques that were adopted into consensus.

    Returns
    -------
    MetricResult with ``name=MetricName.RD`` and value in [0.0, 1.0].
    """
    if not critiques:
        return MetricResult(
            name=MetricName.RD,
            value=0.0,
            description="RD is 0.0 when there are no critiques.",
            details={"total_critiques": 0},
        )

    concrete_count = sum(
        1 for c in critiques if c.get("fix_kind", "").upper() == "CONCRETE_FIX"
    )
    total_count = len(critiques)
    concrete_ratio = concrete_count / total_count

    if adopted_count > 0 and concrete_count > 0:
        adoption_ratio = adopted_count / concrete_count
        rd = concrete_ratio * adoption_ratio
        description = (
            f"Reasoning Depth: {rd:.4f} "
            f"(concrete_fix_ratio={concrete_ratio:.2%}, "
            f"adoption_ratio={adoption_ratio:.2%})."
        )
    else:
        rd = concrete_ratio
        description = (
            f"Reasoning Depth (concrete_fix only): {rd:.4f} "
            f"({concrete_count}/{total_count} critiques have concrete fixes)."
        )

    return MetricResult(
        name=MetricName.RD,
        value=round(rd, 4),
        description=description,
        details={
            "concrete_fix_count": concrete_count,
            "total_critiques": total_count,
            "concrete_fix_ratio": round(concrete_ratio, 4),
            "adopted_count": adopted_count,
        },
    )


# ---------------------------------------------------------------------------
# Metric 7: Hallucination Delta (HD)
# ---------------------------------------------------------------------------


def compute_hd(
    debate_faithfulness: float,
    baseline_faithfulness: float,
) -> MetricResult:
    """Compute Hallucination Delta.

    ``HD = debate_faithfulness - baseline_faithfulness``

    Positive values indicate that DebateEngine produces fewer hallucinations
    than the single-agent baseline.

    Parameters
    ----------
    debate_faithfulness:
        Faithfulness score of the debate output (0.0--1.0).
    baseline_faithfulness:
        Faithfulness score of the single-agent baseline (0.0--1.0).

    Returns
    -------
    MetricResult with ``name=MetricName.HD``.  Value is in [-1.0, 1.0].
    """
    hd = debate_faithfulness - baseline_faithfulness

    if hd > 0:
        qualifier = "fewer hallucinations than baseline"
    elif hd < 0:
        qualifier = "more hallucinations than baseline"
    else:
        qualifier = "same hallucination level as baseline"

    return MetricResult(
        name=MetricName.HD,
        value=round(hd, 4),
        description=(
            f"Hallucination Delta: {hd:+.4f} "
            f"(debate={debate_faithfulness:.4f}, "
            f"baseline={baseline_faithfulness:.4f}, "
            f"{qualifier})."
        ),
        details={
            "debate_faithfulness": debate_faithfulness,
            "baseline_faithfulness": baseline_faithfulness,
        },
    )
