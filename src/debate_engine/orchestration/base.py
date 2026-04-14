"""Base orchestration utilities shared by QuickCritiqueEngine and DebateOrchestrator."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ..providers.llm_provider import CallResult

logger = logging.getLogger(__name__)

# Anonymous role labels used during anonymization
_ANONYMOUS_LABELS = ["Critic Alpha", "Critic Beta", "Critic Gamma"]


def generate_request_id() -> str:
    """Generate a unique request identifier (UUID4)."""
    return str(uuid.uuid4())


def build_role_system_prompt(
    role_type: str,
    task_type: str,
    custom_prompt: str | None = None,
) -> str:
    """Build the system prompt for a critique role.

    Parameters
    ----------
    role_type:
        Role identifier (``"ROLE_A"``, ``"ROLE_B"``, ``"DA_ROLE"``).
    task_type:
        Task type string (e.g. ``"CODE_REVIEW"``).
    custom_prompt:
        Optional user-provided override.  When provided, it replaces the
        default template entirely.

    Returns
    -------
    str
        The complete system prompt for the role.
    """
    if custom_prompt:
        return custom_prompt

    from .role_templates import get_role_template

    try:
        return get_role_template(task_type, role_type)
    except KeyError:
        logger.warning(
            "No template found for task_type=%s role_type=%s; falling back to GENERAL_CRITIQUE",
            task_type,
            role_type,
        )
        from .role_templates import get_role_template as _get

        return _get("GENERAL_CRITIQUE", role_type)


def anonymize_critiques(critiques: list[Any]) -> list[Any]:
    """Replace role identifiers with anonymous labels.

    The mapping is positional: the first critique becomes *Critic Alpha*, the
    second *Critic Beta*, the third *Critic Gamma*.  The ``is_devil_advocate``
    flag is preserved so the Judge can still identify adversarial perspectives.

    Parameters
    ----------
    critiques:
        A list of ``CritiqueSchema`` instances (or any object with a
        ``role_id`` attribute).

    Returns
    -------
    list[Any]
        A **new** list with anonymized ``role_id`` values.  The original
        objects are not mutated; shallow copies are created via ``model_copy``.
    """
    anonymized: list[Any] = []
    for idx, critique in enumerate(critiques):
        label = _ANONYMOUS_LABELS[idx] if idx < len(_ANONYMOUS_LABELS) else f"Critic {idx + 1}"
        if hasattr(critique, "model_copy"):
            copy = critique.model_copy(update={"role_id": label})
        elif hasattr(critique, "role_id"):
            # Fallback for dict-like or non-Pydantic objects
            import copy as _copy

            copy = _copy.copy(critique)
            copy.role_id = label
        else:
            copy = critique
        anonymized.append(copy)
    return anonymized


def build_judge_summary(
    critiques: list[Any],
    quorum_info: tuple[bool, int],
) -> str:
    """Build a structured summary for the Judge from anonymized critiques.

    The summary has three modules:

    1. **Critiques grouped by severity** -- sorted by confidence descending
       within each severity group.
    2. **DA-specific summary** -- all critiques where
       ``is_devil_advocate is True``.
    3. **Quorum status report** -- whether quorum was met and how many
       reviewers succeeded.

    Parameters
    ----------
    critiques:
        Anonymized ``CritiqueSchema`` instances.
    quorum_info:
        ``(quorum_met, success_count)`` tuple from :func:`check_quorum`.

    Returns
    -------
    str
        The structured summary text to feed into the Judge prompt.
    """
    quorum_met, success_count = quorum_info

    # -- Module 1: Critiques grouped by severity --------------------------------
    severity_order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
    sorted_critiques = sorted(
        critiques,
        key=lambda c: (
            severity_order.get(getattr(c, "severity", "MINOR"), 3),
            -getattr(c, "confidence", 0.0),
        ),
    )

    module1_lines = ["## Module 1: Critiques by Severity\n"]
    current_severity: str | None = None
    for c in sorted_critiques:
        sev = getattr(c, "severity", "MINOR")
        if sev != current_severity:
            current_severity = sev
            module1_lines.append(f"### {sev}")
        role_id = getattr(c, "role_id", "Unknown")
        target = getattr(c, "target_area", "unspecified")
        defect = getattr(c, "defect_type", "GENERAL")
        evidence = getattr(c, "evidence", "")
        fix_kind = getattr(c, "fix_kind", "N/A")
        suggested = getattr(c, "suggested_fix", "")
        confidence = getattr(c, "confidence", 0.0)
        is_da = getattr(c, "is_devil_advocate", False)
        da_tag = " [DA]" if is_da else ""

        module1_lines.append(
            f"- [{role_id}{da_tag}] **{target}** -- {defect} "
            f"(confidence={confidence:.2f})\n"
            f"  Evidence: {evidence[:200]}\n"
            f"  Fix kind: {fix_kind} | Suggested: {suggested[:150]}"
        )

    # -- Module 2: DA-specific summary -----------------------------------------
    da_critiques = [c for c in critiques if getattr(c, "is_devil_advocate", False)]
    module2_lines = [
        "\n## Module 2: Devil's Advocate Summary\n",
        f"Total DA critiques: {len(da_critiques)}\n",
    ]
    for c in da_critiques:
        sev = getattr(c, "severity", "MINOR")
        target = getattr(c, "target_area", "unspecified")
        defect = getattr(c, "defect_type", "GENERAL")
        evidence = getattr(c, "evidence", "")
        confidence = getattr(c, "confidence", 0.0)
        module2_lines.append(
            f"- [{sev}] {target}: {defect} (confidence={confidence:.2f})\n"
            f"  Evidence: {evidence[:200]}"
        )

    # -- Module 3: Quorum status report ----------------------------------------
    total_roles = 3
    failed_count = total_roles - success_count
    module3_lines = [
        "\n## Module 3: Quorum Status Report\n",
        f"Quorum met: {quorum_met}",
        f"Successful reviewers: {success_count}/{total_roles}",
        f"Failed reviewers: {failed_count}",
    ]
    if failed_count > 0:
        module3_lines.append(
            "NOTE: Some reviewers failed to respond. Factor this "
            "information gap into your confidence assessment."
        )

    return "\n".join(module1_lines + module2_lines + module3_lines)


def check_quorum(results: list[CallResult]) -> tuple[bool, int]:
    """Check whether the 2/3 quorum is satisfied.

    Parameters
    ----------
    results:
        Call results from each critique role.

    Returns
    -------
    tuple[bool, int]
        ``(quorum_met, success_count)`` where *quorum_met* is ``True`` when
        at least 2 out of 3 roles returned successfully (SUCCESS or
        PARSE_FAILED with content).
    """
    success_count = sum(1 for r in results if r.status in ("SUCCESS", "PARSE_FAILED"))
    quorum_met = success_count >= 2
    return quorum_met, success_count
