"""Markdown formatters for MCP tool output.

Converts DebateEngine Pydantic schemas into human-readable markdown
suitable for display in IDE panels (Claude Code, Cursor, etc.).
"""

from __future__ import annotations

from typing import Any


def _severity_emoji(severity: Any) -> str:
    """Return a visual indicator for a severity level."""
    sev_str = severity.value if hasattr(severity, "value") else str(severity)
    mapping = {
        "CRITICAL": "[CRITICAL]",
        "MAJOR": "[MAJOR]",
        "MINOR": "[MINOR]",
    }
    return mapping.get(sev_str, f"[{sev_str}]")


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def format_consensus_as_markdown(consensus: Any) -> str:
    """Format a ConsensusSchema as readable markdown for IDE display.

    Parameters
    ----------
    consensus:
        A ``ConsensusSchema`` instance from ``debate_engine.schemas``.

    Returns
    -------
    str
        Markdown-formatted string suitable for rendering in an IDE panel.
    """
    lines: list[str] = []

    # Header
    lines.append("# DebateEngine Consensus")
    lines.append("")

    # Partial return warning
    partial = getattr(consensus, "partial_return", False)
    if partial:
        lines.append("> **WARNING: Partial Result** -- The debate did not complete fully. "
                      "Findings below should be treated with reduced confidence.")
        lines.append("")

    # Final conclusion
    conclusion = getattr(consensus, "final_conclusion", "")
    confidence = getattr(consensus, "consensus_confidence", 0.0)
    lines.append("## Conclusion")
    lines.append("")
    lines.append(f"{conclusion}")
    lines.append("")
    lines.append(f"**Confidence:** {confidence:.0%}")
    lines.append("")

    # Metadata summary
    metadata = getattr(consensus, "debate_metadata", None)
    if metadata is not None:
        lines.append("## Metadata")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Request ID | `{getattr(metadata, 'request_id', 'N/A')}` |")
        job_id = getattr(metadata, "job_id", None)
        if job_id:
            lines.append(f"| Job ID | `{job_id}` |")
        task_type = getattr(metadata, "task_type", None)
        task_str = task_type.value if hasattr(task_type, "value") else str(task_type)
        lines.append(f"| Task Type | {task_str} |")
        provider_mode = getattr(metadata, "provider_mode", None)
        pm_str = provider_mode.value if hasattr(provider_mode, "value") else str(provider_mode)
        lines.append(f"| Provider Mode | {pm_str} |")
        lines.append(f"| Rounds Completed | {getattr(metadata, 'rounds_completed', 'N/A')} |")
        lines.append(f"| Quorum Achieved | {getattr(metadata, 'quorum_achieved', 'N/A')} |")
        cost = getattr(metadata, "total_cost_usd", 0.0)
        lines.append(f"| Total Cost | ${cost:.4f} |")
        latency = getattr(metadata, "total_latency_ms", 0.0)
        lines.append(f"| Total Latency | {latency:.0f} ms |")
        models = getattr(metadata, "models_used", [])
        if models:
            lines.append(f"| Models Used | {', '.join(models)} |")
        termination = getattr(metadata, "termination_reason", None)
        term_str = termination.value if hasattr(termination, "value") else str(termination)
        lines.append(f"| Termination | {term_str} |")
        lines.append("")

    # Critiques summary -- grouped by severity
    critiques = getattr(consensus, "critiques_summary", [])
    if critiques:
        lines.append("## Findings")
        lines.append("")

        # Group by severity
        severity_order = ["CRITICAL", "MAJOR", "MINOR"]
        grouped: dict[str, list[Any]] = {}
        for c in critiques:
            sev = c.severity
            sev_str = sev.value if hasattr(sev, "value") else str(sev)
            grouped.setdefault(sev_str, []).append(c)

        for sev_level in severity_order:
            items = grouped.get(sev_level, [])
            if not items:
                continue
            badge = _severity_emoji(sev_level)
            lines.append(f"### {badge} {sev_level} ({len(items)})")
            lines.append("")
            for i, c in enumerate(items, 1):
                role_id = getattr(c, "role_id", None) or "?"
                target = getattr(c, "target_area", "Unknown")
                defect = getattr(c, "defect_type", None)
                defect_str = defect.value if hasattr(defect, "value") else str(defect)
                evidence = getattr(c, "evidence", "")
                fix = getattr(c, "suggested_fix", "")
                fix_kind = getattr(c, "fix_kind", None)
                fix_kind_str = fix_kind.value if hasattr(fix_kind, "value") else str(fix_kind)
                is_da = getattr(c, "is_devil_advocate", False)
                conf = getattr(c, "confidence", 0.0)

                lines.append(f"#### {i}. {target}")
                if is_da:
                    lines.append(f"> *Devil's Advocate* | Role: `{role_id}` | "
                                 f"Confidence: {conf:.0%}")
                else:
                    lines.append(f"> Role: `{role_id}` | Confidence: {conf:.0%}")
                lines.append("")
                lines.append(f"**Defect:** {defect_str}")
                lines.append("")
                lines.append(f"**Evidence:** {_truncate(evidence)}")
                lines.append("")
                lines.append(f"**Suggested Fix** ({fix_kind_str}): {_truncate(fix)}")
                lines.append("")

    # Adopted contributions
    adopted = getattr(consensus, "adopted_contributions", {})
    if adopted:
        lines.append("## Adopted Contributions")
        lines.append("")
        for role_id, contributions in adopted.items():
            lines.append(f"### Role `{role_id}`")
            lines.append("")
            for contrib in contributions:
                lines.append(f"- {contrib}")
            lines.append("")

    # Rejected positions
    rejected = getattr(consensus, "rejected_positions", [])
    if rejected:
        lines.append("## Rejected Positions")
        lines.append("")
        for r in rejected:
            claim = getattr(r, "claim", "")
            reason = getattr(r, "rejection_reason", "")
            lines.append(f"- **Claim:** {_truncate(claim, 200)}")
            lines.append(f"  **Reason:** {_truncate(reason, 200)}")
            lines.append("")

    # Remaining disagreements
    disagreements = getattr(consensus, "remaining_disagreements", [])
    if disagreements:
        lines.append("## Remaining Disagreements")
        lines.append("")
        for d in disagreements:
            lines.append(f"- {d}")
        lines.append("")

    # Minority opinions
    minority = getattr(consensus, "preserved_minority_opinions", [])
    if minority:
        lines.append("## Minority Opinions (Preserved)")
        lines.append("")
        for m in minority:
            opinion = getattr(m, "opinion", "")
            source = getattr(m, "source_role", "?")
            sev = getattr(m, "source_critique_severity", None)
            sev_str = sev.value if hasattr(sev, "value") else str(sev) if sev else "?"
            risk = getattr(m, "potential_risk_if_ignored", "")
            lines.append(f"### Dissent from `{source}` ({sev_str})")
            lines.append("")
            lines.append(f"{opinion}")
            lines.append("")
            lines.append(f"**Risk if ignored:** {_truncate(risk)}")
            lines.append("")

    return "\n".join(lines)


def format_eval_scores_as_markdown(scores: dict[str, Any]) -> str:
    """Format DebateEval metric scores as readable markdown.

    Parameters
    ----------
    scores:
        A dictionary mapping metric names (e.g. ``"BDR"``, ``"FAR"``) to
        either a numeric score or a dict with ``score`` and ``interpretation``
        keys.

    Returns
    -------
    str
        Markdown-formatted evaluation report.
    """
    lines: list[str] = []

    lines.append("# DebateEval Scores")
    lines.append("")

    # Metric descriptions for context
    metric_info: dict[str, str] = {
        "BDR": "Bug Discovery Rate -- fraction of real bugs found (code review)",
        "FAR": "False Alarm Rate -- fraction of flagged issues that are false positives",
        "CV": "Consensus Validity -- accuracy of the consensus answer",
        "CIS": "Conformity Impact Score -- whether stance changes are evidence-driven (anti-sycophancy)",
        "CE": "Convergence Efficiency -- cost-effectiveness of reaching consensus",
        "RD": "Reasoning Depth -- quality and specificity of suggested fixes",
        "HD": "Hallucination Delta -- faithfulness of RAG outputs (RAG tasks)",
    }

    lines.append("| Metric | Score | Interpretation |")
    lines.append("|---|---|---|")

    for metric_name, value in scores.items():
        if isinstance(value, dict):
            score = value.get("score", "N/A")
            interpretation = value.get("interpretation", "")
        else:
            score = value
            interpretation = ""

        # Format score
        if isinstance(score, float):
            score_str = f"{score:.4f}"
        else:
            score_str = str(score)

        # Add description to interpretation
        description = metric_info.get(metric_name, "")
        if description and interpretation:
            full_interp = f"{interpretation} ({description})"
        elif description:
            full_interp = description
        else:
            full_interp = interpretation

        lines.append(f"| **{metric_name}** | {score_str} | {full_interp} |")

    lines.append("")

    # Summary assessment
    numeric_scores = [
        v["score"] if isinstance(v, dict) else v
        for v in scores.values()
        if isinstance(v, (int, float)) or (isinstance(v, dict) and isinstance(v.get("score"), (int, float)))
    ]
    if numeric_scores:
        avg = sum(numeric_scores) / len(numeric_scores)
        lines.append(f"**Average Score:** {avg:.4f} ({len(numeric_scores)} metrics)")
        lines.append("")

    return "\n".join(lines)
