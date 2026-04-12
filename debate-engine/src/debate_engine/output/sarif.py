import json
from typing import Dict, Any
from ..schemas import ConsensusSchema, Severity


def consensus_to_sarif(consensus: ConsensusSchema) -> Dict[str, Any]:
    """将共识转换为 SARIF 格式"""
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "DebateEngine",
                        "version": "0.2.0",
                        "informationUri": "https://github.com/1235357/debate-engine",
                        "rules": []
                    }
                },
                "results": []
            }
        ]
    }
    
    # 构建规则
    rules = {}
    for critique in consensus.critiques_summary:
        rule_id = f"DE-{critique.defect_type.value}"
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": critique.defect_type.value,
                "shortDescription": {
                    "text": critique.defect_type.value
                },
                "fullDescription": {
                    "text": critique.defect_type.value
                },
                "defaultConfiguration": {
                    "level": severity_to_sarif_level(critique.severity)
                }
            }
    
    sarif["runs"][0]["tool"]["driver"]["rules"] = list(rules.values())
    
    # 构建结果
    results = []
    for i, critique in enumerate(consensus.critiques_summary):
        result = {
            "ruleId": f"DE-{critique.defect_type.value}",
            "level": severity_to_sarif_level(critique.severity),
            "message": {
                "text": f"{critique.target_area}: {critique.evidence}"
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": "unknown"
                        },
                        "region": {
                            "startLine": 1,
                            "startColumn": 1
                        }
                    }
                }
            ],
            "properties": {
                "suggestedFix": critique.suggested_fix,
                "confidence": critique.confidence
            }
        }
        results.append(result)
    
    sarif["runs"][0]["results"] = results
    
    return sarif


def severity_to_sarif_level(severity: Severity) -> str:
    """将严重程度转换为 SARIF 级别"""
    if severity == Severity.CRITICAL:
        return "error"
    elif severity == Severity.MAJOR:
        return "warning"
    else:
        return "note"
