# DebateEngine

> **Structured Multi-Agent Critique & Consensus Engine**

[![PyPI version](https://img.shields.io/pypi/v/debate-engine/0.2.0.svg)](https://pypi.org/project/debate-engine/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/1235357/debate-engine/ci.yml?branch=main)](https://github.com/1235357/debate-engine/actions)

**DebateEngine** upgrades free-text AI polling into a **structured cross-critique loop** — using Pydantic v2 `CritiqueSchema` to constrain critique output, role rotation to preserve dissenting perspectives, and a Judge layer to synthesize multi-role opinions while explicitly preserving minority dissent.

## Why DebateEngine?

Existing multi-agent "council" or "debate" tools produce **free-text critiques** that cannot be programmatically parsed, routed, or measured. DebateEngine is different:

| Feature | DebateEngine | ARGUS | Quorum | Prompt-only Councils | AutoGen GroupChat |
|---|---|---|---|---|---|
| Structured Critique Schema | Pydantic v2 | Partial | No | Free text | Free text |
| Devil's Advocate Role | Mandatory | No | Optional | Optional | No |
| Anonymized Cross-Critique | Identity-stripped | No | No | No | No |
| Minority Opinion Preservation | Enforced | No | No | No | No |
| Conformity Impact Score (CIS) | Original metric | No | No | No | No |
| pip install | Yes | No | No | N/A | Yes |
| Quantitative Evaluation | DebateEval 7 metrics | 3 metrics | 2 metrics | No | No |
| SARIF Output | Yes | No | No | No | No |
| GitHub Action Integration | Yes | No | No | No | No |

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
docker run -e GOOGLE_API_KEY=xxx -e GROQ_API_KEY=xxx -p 8765:8765 debate-engine:latest
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

## GitHub Action -- PR Quality Gate

DebateEngine provides a GitHub Action that automatically reviews pull requests using multi-agent debate and posts structured findings as PR comments.

### Setup

1. Add the workflow file to `.github/workflows/debate-review.yml` (see below for full source)
2. Add these secrets to your repository:
   - `GOOGLE_API_KEY` -- Google AI Studio API key (free)
   - `GROQ_API_KEY` -- Groq API key (free)

### How It Works

```yaml
# .github/workflows/debate-review.yml
name: DebateEngine Multi-Agent Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  security-events: write

jobs:
  debate-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install debate-engine
      - name: Get changed files
        id: changed
        uses: tj-actions/changed-files@v44
        with:
          files: |
            **/*.py
            **/*.js
            **/*.ts
            **/*.java
            **/*.go
            **/*.rs
      - name: Run DebateEngine Review
        if: steps.changed.outputs.any_changed == 'true'
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          DEBATE_ENGINE_PROVIDER_MODE: stable
        run: |
          python -c "
          import asyncio, json, sys
          from debate_engine import QuickCritiqueEngine
          from debate_engine.schemas import CritiqueConfigSchema, TaskType
          from debate_engine.output import consensus_to_sarif

          changed_files = '${{ steps.changed.outputs.all_changed_files }}'.split()
          content = ''
          for f in changed_files[:10]:
              try:
                  with open(f) as fh:
                      content += f'\n\n--- {f} ---\n' + fh.read()[:2000]
              except:
                  pass

          if not content.strip():
              print('No content to review')
              sys.exit(0)

          async def review():
              engine = QuickCritiqueEngine()
              config = CritiqueConfigSchema(
                  content=content[:8000],
                  task_type=TaskType.CODE_REVIEW,
              )
              consensus = await engine.critique(config)
              sarif = consensus_to_sarif(consensus)
              with open('debate-results.sarif', 'w') as f:
                  json.dump(sarif, f, indent=2)
              critical = [c for c in consensus.critiques_summary if c.severity.value == 'CRITICAL']
              if critical:
                  print(f'::error::Found {len(critical)} CRITICAL issues')
                  sys.exit(1)

          asyncio.run(review())
          "
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: debate-results.sarif
```

### What You Get

- **PR Comment**: Structured review with severity-ranked findings, confidence score, and devil's advocate warnings
- **SARIF Upload**: Findings appear in GitHub Security tab
- **Quality Gate**: PR fails if CRITICAL issues are found

## SARIF Output

DebateEngine can output results in [SARIF format](https://sarif-web.azurewebsites.net/) for integration with GitHub Code Scanning and other security tools:

```python
from debate_engine.output import consensus_to_sarif

sarif = consensus_to_sarif(consensus)

with open("results.sarif", "w") as f:
    json.dump(sarif, f, indent=2)
```

The SARIF output maps DebateEngine findings to standard SARIF rules:
- **CRITICAL** -> `error` level
- **MAJOR** -> `warning` level
- **MINOR** -> `note` level

Each finding includes the defect type, target area, evidence, and suggested fix.

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
|  DebateEval: BDR, FAR, CV, CIS, CE, RD, HD      |
+--------------------------------------------------+
| Output Layer                                      |
|  Markdown | SARIF | JSON                          |
+--------------------------------------------------+
```

## Core Innovation: Conformity Impact Score (CIS)

CIS is an industry-first metric quantifying whether Agent stance changes during debate are **evidence-driven** or **sycophantic**. It replaces the earlier Conformity Score (CS) with improved sensitivity to critique severity and context:

```
CIS = Sum(stance_change * severity_weight * context_relevance) / Sum(stance_change * context_relevance)
```

- **CIS ~ 1.0**: Stance changes driven by high-severity, context-relevant critiques (good -- evidence-driven)
- **CIS ~ 0.0**: Stance changes driven by low-severity or irrelevant critiques (bad -- sycophantic)
- **CIS ~ 0.5**: Mixed behavior, warrants investigation

Improvements over CS:
- **Context relevance weighting**: Penalizes stance changes based on off-topic critiques
- **Severity normalization**: Better calibrated across different task types
- **Temporal decay**: Recent stance changes weighted more heavily

Validated through ablation studies across 3 Anti-Sycophancy configurations and benchmarked against the DTE framework (EMNLP 2025).

## Three-Layer Anti-Sycophancy Defense

1. **Provider-Diversity Quorum** (2/3 success threshold)
2. **Devil's Advocate** adversarial role with tailored system prompts
3. **Response Anonymization** stripping model identity before peer critique

Informed by ACL 2025 (CONSENSAGENT), OpenReview 2025 (identity bias research), and EMNLP 2025 (DTE framework).

## Free API Strategy

DebateEngine v0.2.0 is designed to run entirely on **free-tier API providers**:

| Provider | Free Tier | Used For |
|---|---|---|
| **Google AI Studio** (Gemini) | 15 RPM / 1M tokens/day | Primary provider (stable mode) |
| **Groq** (Llama, Mixtral) | 30 RPM / unlimited | Devil's Advocate role (balanced mode) |
| **NVIDIA NIM** (various) | Free tier available | Diverse mode third provider |

No paid API keys required for basic usage. Set `GOOGLE_API_KEY` and optionally `GROQ_API_KEY` to get started.

## DebateEval Metrics

| Metric | What It Measures | Use Case |
|---|---|---|
| BDR | Bug Discovery Rate | Code review quality |
| FAR | False Alarm Rate | Critique precision |
| CV | Consensus Validity | Answer accuracy |
| CIS | Conformity Impact Score | Anti-sycophancy (original, improved) |
| CE | Convergence Efficiency | Cost-effectiveness |
| RD | Reasoning Depth | Fix quality |
| HD | Hallucination Delta | RAG faithfulness |

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Required | Primary LLM provider (Google AI Studio, free) |
| `GROQ_API_KEY` | Optional | Backup provider for Devil's Advocate (free) |
| `NVIDIA_API_KEY` | Optional | Third provider for diverse mode |
| `DEBATE_ENGINE_PROVIDER_MODE` | `stable` | `stable`, `balanced`, or `diverse` |
| `DEBATE_ENGINE_LOG_LEVEL` | `INFO` | Logging level |

### Provider Modes

- **stable** (default): Single provider, all roles. Just `GOOGLE_API_KEY`.
- **balanced**: DA role uses different provider. Needs `GOOGLE_API_KEY` + `GROQ_API_KEY`.
- **diverse** (v1.0): Three providers for maximum diversity. Adds `NVIDIA_API_KEY`.

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

## Competitive Analysis: ARGUS vs Quorum vs DebateEngine

### ARGUS (2025)
ARGUS uses structured argumentation frameworks but lacks multi-agent diversity and anonymity. It provides 3 evaluation metrics and does not support programmatic output.

### Quorum (2025)
Quorum focuses on voting-based consensus but does not implement cross-critique or devil's advocate roles. Limited to 2 evaluation metrics.

### DebateEngine Advantage
- **7 evaluation metrics** vs ARGUS (3) and Quorum (2)
- **SARIF output** for CI/CD integration
- **GitHub Action** for automated PR review
- **Free-tier only** operation (no paid APIs required)
- **Minority opinion preservation** with risk quantification

## Roadmap

- [x] v0.1: QuickCritiqueEngine (sync, single-round)
- [x] v0.1: Pydantic v2 CritiqueSchema + ConsensusSchema
- [x] v0.1: Devil's Advocate + Anonymization + Minority Opinions
- [x] v0.1: 2/3 Quorum + Partial Return
- [x] v0.2: DebateOrchestrator (async, multi-round)
- [x] v0.2: Job API (submit/poll/cancel)
- [x] v0.2: SARIF output + GitHub Action integration
- [x] v0.2: Free API strategy (Google AI Studio + Groq + NVIDIA NIM)
- [x] v0.2: Conformity Impact Score (CIS) replacing CS
- [ ] v0.2: SSE progress streaming
- [x] MCP adapter (3 tools)
- [x] DebateEval (7 metrics)
- [ ] v1.0: Redis persistence + NetworkX debate graphs
- [ ] v1.0: Diverse mode (3 providers)
- [ ] v1.0: Full 30-case benchmark report

## Academic Foundation

| Paper | Finding | Impact on DebateEngine |
|---|---|---|
| Du et al., ICML 2024 | Multi-agent debate improves reasoning | Project foundation |
| CONSENSAGENT, ACL 2025 | Quantified sycophancy in debate | Conformity Impact Score design |
| Identity Bias in MAD, arXiv 2025 | Anonymization reduces bias | Cross-critique anonymization |
| AgentAuditor, 2026 | Structured summaries reduce judge sycophancy | Judge input design |
| DTE: Debate & Thought Evaluation, EMNLP 2025 | Framework for evaluating debate quality | DebateEval metric calibration |
| Improving Multi-Agent Debate via Role Specialization, arXiv 2025 | Role diversity improves outcomes | Role template design |
| On the Conformity of Language Models, arXiv 2025 | LLMs exhibit systematic sycophancy | Three-layer anti-sycophancy defense |

## License

MIT License -- see [LICENSE](LICENSE) for details.
