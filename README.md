# DebateEngine

> **Structured Multi-Agent Critique & Consensus Engine**

[![PyPI version](https://img.shields.io/pypi/v/debate-engine.svg)](https://pypi.org/project/debate-engine/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DebateEngine** upgrades free-text AI polling into a **structured cross-critique loop** — using Pydantic v2 `CritiqueSchema` to constrain critique output, role rotation to preserve dissenting perspectives, and a Judge layer to synthesize multi-role opinions while explicitly preserving minority dissent.

## Why DebateEngine?

Existing multi-agent "council" or "debate" tools produce **free-text critiques** that cannot be programmatically parsed, routed, or measured. DebateEngine is different:

| Feature | DebateEngine | Prompt-only Councils | AutoGen GroupChat |
|---|---|---|---|
| Structured Critique Schema | Pydantic v2 | Free text | Free text |
| Devil's Advocate Role | Mandatory | Optional | No |
| Anonymized Cross-Critique | Identity-stripped | No | No |
| Minority Opinion Preservation | Enforced | No | No |
| Conformity Score (CS) | Original metric | No | No |
| pip install | Yes | N/A | Yes |
| Quantitative Evaluation | DebateEval 7 metrics | No | No |

## Quick Start

### Installation

```bash
pip install debate-engine
```

With MCP support:

```bash
pip install "debate-engine[mcp]"
```

### Python API

```python
import asyncio
from debate_engine import QuickCritiqueEngine
from debate_engine.schemas import CritiqueConfigSchema, TaskType

async def main():
    engine = QuickCritiqueEngine()

    config = CritiqueConfigSchema(
        content='''def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)''',
        task_type=TaskType.CODE_REVIEW,
    )

    consensus = await engine.critique(config)
    print(consensus.final_conclusion)
    print(f"Confidence: {consensus.consensus_confidence}")
    for critique in consensus.critiques_summary:
        print(f"  [{critique.severity.value}] {critique.target_area}: {critique.evidence[:100]}")

asyncio.run(main())
```

### REST API

```bash
# Start the server
debate-engine serve

# Quick critique
curl -X POST http://localhost:8765/v1/quick-critique \
  -H "Content-Type: application/json" \
  -d '{"content": "Your code or proposal here...", "task_type": "CODE_REVIEW"}'

# Submit async debate
curl -X POST http://localhost:8765/v1/debate \
  -H "Content-Type: application/json" \
  -d '{"content": "Your proposal...", "max_rounds": 2}'
```

### Docker

```bash
docker run -e OPENAI_API_KEY=sk-xxx -p 8765:8765 debate-engine:latest
```

### MCP (Claude Code / Cursor)

Add to your MCP settings:

```json
{
  "mcpServers": {
    "debate-engine": {
      "command": "debate-engine",
      "args": ["mcp"]
    }
  }
}
```

Available tools: `debate_quick_critique`, `debate_full`, `debate_eval_score`

## Architecture

```
+--------------------------------------------------+
| Entry Layer                                       |
|  Python API | FastAPI REST | MCP Server           |
+--------------------------------------------------+
| Orchestration Layer                               |
|  QuickCritiqueEngine (v0.1 sync)                 |
|  DebateOrchestrator (v0.2 async)                 |
+--------------------------------------------------+
| Provider Layer                                    |
|  LiteLLM (100+ providers) | 3 modes:             |
|  stable | balanced | diverse                     |
+--------------------------------------------------+
| Schema Layer (Pydantic v2)                        |
|  CritiqueSchema | ConsensusSchema | Config       |
+--------------------------------------------------+
| Evaluation Layer                                  |
|  DebateEval: BDR, FAR, CV, CS, CE, RD, HD        |
+--------------------------------------------------+
```

## Core Innovation: Conformity Score (CS)

CS is an industry-first metric quantifying whether Agent stance changes during debate are **evidence-driven** or **sycophantic**:

```
CS = Sum(stance_change * severity_weight) / Sum(stance_change)
```

- **CS ~ 1.0**: Stance changes driven by high-severity critiques (good -- evidence-driven)
- **CS ~ 0.0**: Stance changes driven by low-severity critiques (bad -- sycophantic)

Validated through ablation studies across 3 Anti-Sycophancy configurations.

## Three-Layer Anti-Sycophancy Defense

1. **Provider-Diversity Quorum** (2/3 success threshold)
2. **Devil's Advocate** adversarial role with tailored system prompts
3. **Response Anonymization** stripping model identity before peer critique

Informed by ACL 2025 (CONSENSAGENT) and OpenReview 2025 (identity bias research).

## DebateEval Metrics

| Metric | What It Measures | Use Case |
|---|---|---|
| BDR | Bug Discovery Rate | Code review quality |
| FAR | False Alarm Rate | Critique precision |
| CV | Consensus Validity | Answer accuracy |
| CS | Conformity Score | Anti-sycophancy (original) |
| CE | Convergence Efficiency | Cost-effectiveness |
| RD | Reasoning Depth | Fix quality |
| HD | Hallucination Delta | RAG faithfulness |

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | Required | Primary LLM provider API key |
| `ANTHROPIC_API_KEY` | Optional | Backup provider (balanced mode) |
| `DEBATE_ENGINE_PROVIDER_MODE` | `stable` | `stable`, `balanced`, or `diverse` |
| `DEBATE_ENGINE_LOG_LEVEL` | `INFO` | Logging level |

### Provider Modes

- **stable** (default): Single provider, all roles. Just `OPENAI_API_KEY`.
- **balanced**: DA role uses different provider. Needs both keys.
- **diverse** (v1.0): Three providers for maximum diversity.

## MCP Tools Reference

### `debate_quick_critique`

Single-round multi-role critique. Returns structured markdown with severity-ranked findings.

**Parameters:**
- `content` (str): Text to critique
- `task_type` (str, optional): `AUTO`, `CODE_REVIEW`, `RAG_VALIDATION`, `ARCHITECTURE_DECISION`

**Latency:** 5-15 seconds

### `debate_full`

Multi-round debate with proposals, cross-critique, revisions, and judge consensus.

**Parameters:**
- `content` (str): Proposal or content to debate
- `task_type` (str, optional): Same options as quick critique
- `max_rounds` (int, optional): 1 or 2, default 2

**Latency:** 30-120 seconds

### `debate_eval_score`

Evaluate an existing consensus result using DebateEval metrics.

**Parameters:**
- `consensus_json` (str): JSON string of a ConsensusSchema result
- `metrics` (str, optional): Comma-separated metrics, default `BDR,FAR,CV,RD`

## Roadmap

- [x] v0.1: QuickCritiqueEngine (sync, single-round)
- [x] v0.1: Pydantic v2 CritiqueSchema + ConsensusSchema
- [x] v0.1: Devil's Advocate + Anonymization + Minority Opinions
- [x] v0.1: 2/3 Quorum + Partial Return
- [x] v0.2: DebateOrchestrator (async, multi-round)
- [x] v0.2: Job API (submit/poll/cancel)
- [ ] v0.2: SSE progress streaming
- [x] MCP adapter (3 tools)
- [x] DebateEval (7 metrics)
- [ ] v1.0: Redis persistence + NetworkX debate graphs
- [ ] v1.0: Diverse mode (3 providers)
- [ ] v1.0: Full 30-case benchmark report
- [ ] v1.0: GitHub Actions CI/CD

## Academic Foundation

| Paper | Finding | Impact on DebateEngine |
|---|---|---|
| Du et al., ICML 2024 | Multi-agent debate improves reasoning | Project foundation |
| CONSENSAGENT, ACL 2025 | Quantified sycophancy in debate | Conformity Score design |
| Identity Bias in MAD, 2025 | Anonymization reduces bias | Cross-critique anonymization |
| AgentAuditor, 2026 | Structured summaries reduce judge sycophancy | Judge input design |

## License

MIT License -- see [LICENSE](LICENSE) for details.
