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

    # Get metadata for context
    metadata = getattr(consensus, "debate_metadata", None)
    reviewed_file = (
        getattr(metadata, "reviewed_file", "reviewed-content") if metadata else "reviewed-content"
    )

    for idx, critique in enumerate(critiques):
        defect_type = getattr(critique, "defect_type", None)
        defect_value = defect_type.value if hasattr(defect_type, "value") else str(defect_type)  # type: ignore[union-attr]
        severity = getattr(critique, "severity", None)
        sev_value = severity.value if hasattr(severity, "value") else str(severity)  # type: ignore[union-attr]
        target = getattr(critique, "target_area", "")
        evidence = getattr(critique, "evidence", "")
        fix = getattr(critique, "suggested_fix", "")
        confidence = getattr(critique, "confidence", 0.0)
        is_da = getattr(critique, "is_devil_advocate", False)

        # Map severity to SARIF level
        level = (
            "error" if sev_value == "CRITICAL" else "warning" if sev_value == "MAJOR" else "note"
        )

        # Create rule ID and metadata
        rule_id = defect_value.lower().replace(" ", "_")
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "shortDescription": {"text": defect_value},
                "fullDescription": {"text": f"{defect_value} detected during debate analysis"},
                "help": {"text": f"This rule identifies {defect_value.lower()}."},
                "helpUri": "https://github.com/1235357/debate-engine#severity-levels",
                "properties": {
                    "category": "Code Quality",
                    "precision": "high"
                    if confidence > 0.7
                    else "medium"
                    if confidence > 0.4
                    else "low",
                },
            }

        # Build physical location with region if available
        physical_location = {"artifactLocation": {"uri": reviewed_file, "uriBaseId": "%SRCROOT%"}}

        # Add region information if available (placeholder for now)
        # In a real implementation, this would come from the critique or metadata
        region = getattr(critique, "region", None)
        if region:
            physical_location["region"] = region
        else:
            # Add a default region as placeholder
            physical_location["region"] = {
                "startLine": 1,
                "startColumn": 1,
                "endLine": 1,
                "endColumn": 1,
            }

        # Create result
        result = {
            "ruleId": rule_id,
            "level": level,
            "message": {
                "text": f"[{sev_value}] {target}\n\nEvidence: {evidence}\n\nSuggested Fix: {fix}"
            },
            "locations": [{"physicalLocation": physical_location}],
            "properties": {
                "confidence": confidence,
                "is_devil_advocate": is_da,
                "severity": sev_value,
            },
        }

        results.append(result)

    # Build SARIF output
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "DebateEngine",
                        "version": "0.2.0",
                        "informationUri": "https://github.com/1235357/debate-engine",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "columnKind": "utf16CodeUnits",
                "properties": {
                    "github": {
                        "codeScanning": {
                            "alertSeverity": "high"
                            if any(r["level"] == "error" for r in results)
                            else "medium"
                        }
                    }
                },
            }
        ],
    }

    return sarif
