"""SARIF output support for DebateEngine.

Converts ConsensusSchema to SARIF v2.1.0 format, compatible with
GitHub Code Scanning and other SARIF-consuming tools.
"""

from __future__ import annotations

from typing import Any


def consensus_to_sarif(consensus: Any) -> dict[str, Any]:
    """Convert a ConsensusSchema to SARIF v2.1.0 format."""
    results = []
    rules = {}
    critiques = getattr(consensus, "critiques_summary", []) or []
    for idx, critique in enumerate(critiques):
        defect_type = getattr(critique, "defect_type", None)
        defect_value = defect_type.value if hasattr(defect_type, "value") else str(defect_type)
        severity = getattr(critique, "severity", None)
        sev_value = severity.value if hasattr(severity, "value") else str(severity)
        target = getattr(critique, "target_area", "")
        evidence = getattr(critique, "evidence", "")
        fix = getattr(critique, "suggested_fix", "")
        confidence = getattr(critique, "confidence", 0.0)
        is_da = getattr(critique, "is_devil_advocate", False)
        level = "error" if sev_value == "CRITICAL" else "warning" if sev_value == "MAJOR" else "note"
        rule_id = defect_value.lower().replace(" ", "_")
        if rule_id not in rules:
            rules[rule_id] = {"id": rule_id, "shortDescription": {"text": defect_value}, "helpUri": "https://github.com/1235357/debate-engine#severity-levels"}
        result = {"ruleId": rule_id, "level": level, "message": {"text": f"[{sev_value}] {target}\n\nEvidence: {evidence}\n\nSuggested Fix: {fix}"}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": "reviewed-content"}}}], "properties": {"confidence": confidence, "is_devil_advocate": is_da}}
        results.append(result)
    sarif = {"$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json", "version": "2.1.0", "runs": [{"tool": {"driver": {"name": "DebateEngine", "version": "0.2.0", "informationUri": "https://github.com/1235357/debate-engine", "rules": list(rules.values())}}, "results": results, "columnKind": "utf16CodeUnits"}]}
    return sarif