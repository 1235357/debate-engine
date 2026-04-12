from typing import Optional
from ..schemas import ConsensusSchema, Severity


def generate_pr_comment(consensus: ConsensusSchema) -> str:
    """生成 GitHub PR 评论"""
    comment = f"## DebateEngine Multi-Agent Review\n\n"
    comment += f"**Confidence:** {consensus.consensus_confidence:.0%}\n\n"
    comment += "| Severity | Count |\n|----------|-------|\n"
    comment += f"| CRITICAL | {consensus.critical_critiques} |\n"
    comment += f"| MAJOR | {consensus.major_critiques} |\n"
    comment += f"| MINOR | {consensus.minor_critiques} |\n\n"
    
    for critique in consensus.critiques_summary:
        emoji = '🔴' if critique.severity == Severity.CRITICAL else '🟡' if critique.severity == Severity.MAJOR else '🟢'
        comment += f"{emoji} **[{critique.severity.value}] {critique.defect_type.value}** — {critique.target_area}\n"
        comment += f"> {critique.evidence[:200]}\n"
        comment += f"> **Fix:** {critique.suggested_fix[:200]}\n\n"
    
    if consensus.preserved_minority_opinions:
        comment += "### Devil's Advocate Findings\n"
        for mo in consensus.preserved_minority_opinions:
            comment += f"- ⚠️ {mo.opinion[:200]} (Risk: {mo.potential_risk_if_ignored[:100]})\n"
    
    return comment
