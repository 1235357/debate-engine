"""DebateEngine MCP Server - Thin adapter exposing 3 tools.

This is a THIN adapter layer. It does NOT contain business logic.
All logic is delegated to the existing engine classes
(QuickCritiqueEngine, DebateOrchestrator) from the orchestration layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .formatters import format_consensus_as_markdown, format_eval_scores_as_markdown

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="debate-engine"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_task_type(task_type: str) -> Any:
    """Resolve a task_type string to the TaskType enum."""
    from debate_engine.schemas import TaskType

    try:
        return TaskType(task_type)
    except ValueError:
        return TaskType.AUTO


def _parse_consensus_json(consensus_json: str) -> Any:
    """Parse a JSON string into a ConsensusSchema.

    Accepts either a raw JSON string or a ConsensusSchema-compatible dict.
    """
    from debate_engine.schemas import ConsensusSchema

    data = json.loads(consensus_json)

    # If it's already a dict that matches ConsensusSchema fields, validate it
    if isinstance(data, dict):
        return ConsensusSchema.model_validate(data)

    raise ValueError(
        "consensus_json must be a JSON object matching ConsensusSchema fields."
    )


# ---------------------------------------------------------------------------
# Tool: debate_quick_critique
# ---------------------------------------------------------------------------


@mcp.tool()
async def debate_quick_critique(
    content: str,
    task_type: str = "AUTO",
) -> str:
    """Perform a multi-role structured critique analysis on the given content.

    Returns a structured consensus with severity-ranked findings, evidence,
    and actionable fixes. Three reviewer roles analyze concurrently:
    - Domain Expert (finds domain-specific issues)
    - Quality Analyst (checks reasoning and completeness)
    - Devil's Advocate (challenges assumptions, finds edge cases)

    Args:
        content: The text to critique (code, architecture proposal, RAG output, etc.)
        task_type: Type of critique - AUTO, CODE_REVIEW, RAG_VALIDATION, or ARCHITECTURE_DECISION

    Returns:
        Structured critique consensus in markdown format with:
        - Final conclusion and confidence score
        - Severity-ranked findings (CRITICAL/MAJOR/MINOR)
        - Evidence and suggested fixes for each finding
        - Preserved minority opinions from Devil's Advocate
    """
    from debate_engine.orchestration import QuickCritiqueEngine
    from debate_engine.schemas import CritiqueConfigSchema

    task_enum = _resolve_task_type(task_type)

    config = CritiqueConfigSchema(
        content=content,
        task_type=task_enum,
    )

    engine = QuickCritiqueEngine()

    try:
        consensus = await engine.critique(config)
    except Exception as exc:
        logger.exception("debate_quick_critique failed: %s", exc)
        return (
            f"## Error\n\n"
            f"Quick critique failed: {exc}\n\n"
            f"Please check your API key configuration and try again."
        )

    return format_consensus_as_markdown(consensus)


# ---------------------------------------------------------------------------
# Tool: debate_full
# ---------------------------------------------------------------------------


@mcp.tool()
async def debate_full(
    content: str,
    task_type: str = "AUTO",
    max_rounds: int = 2,
) -> str:
    """Run a full multi-round debate with proposal, cross-critique, revision, and judge consensus.

    More thorough than quick_critique but takes longer (30-120 seconds).
    Uses async job submission with internal polling.

    Args:
        content: The proposal or content to debate
        task_type: AUTO, CODE_REVIEW, RAG_VALIDATION, or ARCHITECTURE_DECISION
        max_rounds: Number of debate rounds (1 or 2, default 2)

    Returns:
        Full debate consensus with per-round analysis and convergence assessment.
    """
    from debate_engine.orchestration import DebateOrchestrator
    from debate_engine.schemas import DebateConfigSchema

    task_enum = _resolve_task_type(task_type)

    # Clamp max_rounds to valid range
    max_rounds = max(1, min(2, int(max_rounds)))

    config = DebateConfigSchema(
        content=content,
        task_type=task_enum,
        max_rounds=max_rounds,
    )

    orchestrator = DebateOrchestrator()

    try:
        job_id = await orchestrator.submit(config)

        # Poll until completion (with timeout)
        max_wait_seconds = 180
        poll_interval = 2.0
        elapsed = 0.0

        while elapsed < max_wait_seconds:
            status = await orchestrator.get_status(job_id)
            status_str = status.status.value if hasattr(status.status, "value") else str(status.status)

            if status_str == "DONE":
                result = await orchestrator.get_result(job_id)
                if result is not None:
                    return format_consensus_as_markdown(result)
                return (
                    f"## Debate Completed (No Result)\n\n"
                    f"Job `{job_id}` completed but produced no result."
                )

            if status_str in ("FAILED", "CANCELLED"):
                error_msg = status.error.message if status.error else "Unknown error"
                return (
                    f"## Debate {status_str}\n\n"
                    f"Job `{job_id}` ended with status **{status_str}**.\n\n"
                    f"**Error:** {error_msg}"
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        try:
            await orchestrator.cancel(job_id)
        except Exception:
            pass

        return (
            f"## Debate Timeout\n\n"
            f"Job `{job_id}` did not complete within {max_wait_seconds}s. "
            f"Current phase: {getattr(status, 'current_phase', 'unknown')}, "
            f"progress: {getattr(status, 'progress_pct', 0)}%.\n\n"
            f"The job has been cancelled. Try reducing content length or "
            f"setting max_rounds=1 for faster results."
        )

    except Exception as exc:
        logger.exception("debate_full failed: %s", exc)
        return (
            f"## Error\n\n"
            f"Full debate failed: {exc}\n\n"
            f"Please check your API key configuration and try again."
        )


# ---------------------------------------------------------------------------
# Tool: debate_eval_score
# ---------------------------------------------------------------------------


@mcp.tool()
async def debate_eval_score(
    consensus_json: str,
    metrics: str = "BDR,FAR,CV,RD",
) -> str:
    """Evaluate a debate consensus result using DebateEval metrics.

    Computes quality metrics on an existing debate result:
    - BDR: Bug Discovery Rate (code review tasks)
    - FAR: False Alarm Rate
    - CV: Consensus Validity
    - CIS: Conformity Impact Score (anti-sycophancy measure)
    - CE: Convergence Efficiency
    - RD: Reasoning Depth
    - HD: Hallucination Delta (RAG tasks)

    Args:
        consensus_json: JSON string of a ConsensusSchema result
        metrics: Comma-separated list of metrics to compute

    Returns:
        Evaluation scores with interpretations.
    """
    # Parse the consensus JSON
    try:
        consensus = _parse_consensus_json(consensus_json)
    except (json.JSONDecodeError, ValueError) as exc:
        return (
            f"## Error\n\n"
            f"Failed to parse consensus_json: {exc}\n\n"
            f"Please provide a valid JSON object matching ConsensusSchema."
        )

    # Parse requested metrics
    requested = [m.strip().upper() for m in metrics.split(",") if m.strip()]

    # Valid metric names
    valid_metrics = {"BDR", "FAR", "CV", "CIS", "CE", "RD", "HD"}
    invalid = [m for m in requested if m not in valid_metrics]
    if invalid:
        return (
            f"## Error\n\n"
            f"Invalid metric(s): {', '.join(invalid)}\n\n"
            f"Valid metrics: {', '.join(sorted(valid_metrics))}"
        )

    # Compute metrics using heuristic analysis of the consensus
    scores = _compute_metrics(consensus, requested)

    return format_eval_scores_as_markdown(scores)


# ---------------------------------------------------------------------------
# Metric computation (heuristic, no external ML dependencies)
# ---------------------------------------------------------------------------


def _compute_metrics(
    consensus: Any,
    requested_metrics: list[str],
) -> dict[str, Any]:
    """Compute DebateEval metrics from a ConsensusSchema.

    Uses heuristic analysis based on the structured fields in the consensus.
    These are lightweight approximations suitable for quick evaluation.
    For full benchmark evaluation, use the ``debate-engine[eval]`` extras
    with sentence-transformers and RAGAS.

    Parameters
    ----------
    consensus:
        A validated ``ConsensusSchema`` instance.
    requested_metrics:
        List of metric codes to compute.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping of metric name to ``{"score": float, "interpretation": str}``.
    """
    scores: dict[str, dict[str, Any]] = {}

    critiques = getattr(consensus, "critiques_summary", [])
    confidence = getattr(consensus, "consensus_confidence", 0.0)
    metadata = getattr(consensus, "debate_metadata", None)
    minority = getattr(consensus, "preserved_minority_opinions", [])
    rejected = getattr(consensus, "rejected_positions", [])
    partial = getattr(consensus, "partial_return", False)
    quorum = getattr(metadata, "quorum_achieved", False) if metadata else False
    rounds = getattr(metadata, "rounds_completed", 1) if metadata else 1
    cost = getattr(metadata, "total_cost_usd", 0.0) if metadata else 0.0
    latency = getattr(metadata, "total_latency_ms", 0.0) if metadata else 0.0

    # Count severities
    severity_counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0}
    for c in critiques:
        sev = c.severity
        sev_str = sev.value if hasattr(sev, "value") else str(sev)
        severity_counts[sev_str] = severity_counts.get(sev_str, 0) + 1

    total_critiques = len(critiques)

    # --- BDR: Bug Discovery Rate ---
    if "BDR" in requested_metrics:
        # Heuristic: ratio of CRITICAL+MAJOR findings to total findings
        # Higher is better -- indicates the engine found substantive issues
        if total_critiques > 0:
            bdr = (severity_counts["CRITICAL"] + severity_counts["MAJOR"]) / total_critiques
        else:
            bdr = 0.0

        if bdr >= 0.6:
            interp = "Excellent -- engine found predominantly high-severity issues"
        elif bdr >= 0.3:
            interp = "Good -- meaningful mix of severity levels"
        else:
            interp = "Low -- mostly minor findings; may need content with more issues"

        scores["BDR"] = {"score": round(bdr, 4), "interpretation": interp}

    # --- FAR: False Alarm Rate ---
    if "FAR" in requested_metrics:
        # Heuristic: estimate based on confidence and quorum
        # Lower is better -- indicates precise critiques
        if quorum and confidence > 0.5:
            far = max(0.0, 1.0 - confidence)
        elif quorum:
            far = 0.4
        else:
            far = 0.7  # Low confidence / no quorum suggests more false alarms

        if far <= 0.2:
            interp = "Low -- critiques appear precise and well-targeted"
        elif far <= 0.5:
            interp = "Moderate -- some findings may be noise"
        else:
            interp = "High -- many findings may be false positives"

        scores["FAR"] = {"score": round(far, 4), "interpretation": interp}

    # --- CV: Consensus Validity ---
    if "CV" in requested_metrics:
        # Heuristic: based on quorum, confidence, and whether disagreements remain
        remaining = len(getattr(consensus, "remaining_disagreements", []))
        if quorum and confidence >= 0.7 and remaining == 0:
            cv = confidence
        elif quorum and confidence >= 0.4:
            cv = confidence * 0.8
        elif partial:
            cv = 0.2
        else:
            cv = confidence * 0.5

        if cv >= 0.7:
            interp = "Strong -- high confidence consensus with full agreement"
        elif cv >= 0.4:
            interp = "Moderate -- consensus reached but with some reservations"
        else:
            interp = "Weak -- low confidence or incomplete consensus"

        scores["CV"] = {"score": round(cv, 4), "interpretation": interp}

    # --- CIS: Conformity Impact Score ---
    if "CIS" in requested_metrics:
        # Heuristic: based on minority opinions preserved and rejected positions
        # CIS near 1.0 = evidence-driven stance changes (good)
        # CIS near 0.0 = sycophantic agreement (bad)
        if total_critiques > 0:
            # Having minority opinions and rejected positions is a sign of
            # healthy debate (not sycophantic)
            dissent_signals = len(minority) + len(rejected)
            cis = min(1.0, dissent_signals / max(1, total_critiques))
        else:
            cis = 0.5  # Neutral when no data

        if cis >= 0.7:
            interp = "Healthy -- significant dissent preserved, low sycophancy risk"
        elif cis >= 0.3:
            interp = "Moderate -- some dissent preserved"
        else:
            interp = "Low -- little dissent preserved; may indicate sycophantic agreement"

        scores["CIS"] = {"score": round(cis, 4), "interpretation": interp}

    # --- CE: Convergence Efficiency ---
    if "CE" in requested_metrics:
        # Heuristic: did the debate converge quickly and cheaply?
        # Higher is better
        if rounds == 1 and quorum:
            ce = 0.9  # Converged in 1 round -- very efficient
        elif rounds == 2 and quorum:
            ce = 0.7  # Needed 2 rounds but converged
        elif rounds == 2 and not quorum:
            ce = 0.3  # 2 rounds and still no quorum
        else:
            ce = 0.5  # Partial or other

        # Penalize for high cost
        if cost > 0.5:
            ce *= 0.7

        if ce >= 0.7:
            interp = "Efficient -- debate converged quickly within budget"
        elif ce >= 0.4:
            interp = "Acceptable -- debate required multiple rounds"
        else:
            interp = "Inefficient -- high cost or failed convergence"

        scores["CE"] = {"score": round(ce, 4), "interpretation": interp}

    # --- RD: Reasoning Depth ---
    if "RD" in requested_metrics:
        # Heuristic: based on evidence length, fix specificity, and critique count
        if total_critiques > 0:
            total_evidence_len = sum(len(getattr(c, "evidence", "")) for c in critiques)
            total_fix_len = sum(len(getattr(c, "suggested_fix", "")) for c in critiques)
            avg_evidence = total_evidence_len / total_critiques
            avg_fix = total_fix_len / total_critiques

            # Normalize: good evidence > 100 chars, good fix > 80 chars
            evidence_score = min(1.0, avg_evidence / 200.0)
            fix_score = min(1.0, avg_fix / 150.0)
            rd = (evidence_score * 0.5 + fix_score * 0.5)
        else:
            rd = 0.0

        if rd >= 0.7:
            interp = "Deep -- detailed evidence and specific fix suggestions"
        elif rd >= 0.4:
            interp = "Moderate -- reasonable but could be more specific"
        else:
            interp = "Shallow -- brief evidence or vague fix suggestions"

        scores["RD"] = {"score": round(rd, 4), "interpretation": interp}

    # --- HD: Hallucination Delta ---
    if "HD" in requested_metrics:
        # Heuristic: check for factual error flags and evidence grounding
        factual_errors = sum(
            1 for c in critiques
            if hasattr(c, "defect_type")
            and (
                (hasattr(c.defect_type, "value") and c.defect_type.value == "FACTUAL_ERROR")
                or str(c.defect_type) == "FACTUAL_ERROR"
            )
        )

        if total_critiques > 0:
            # Lower factual error rate = lower hallucination risk
            hd = 1.0 - (factual_errors / total_critiques)
        else:
            hd = 0.5  # Neutral

        if hd >= 0.9:
            interp = "Low hallucination risk -- few factual errors detected"
        elif hd >= 0.6:
            interp = "Moderate -- some factual concerns raised"
        else:
            interp = "High hallucination risk -- multiple factual errors flagged"

        scores["HD"] = {"score": round(hd, 4), "interpretation": interp}

    return scores
