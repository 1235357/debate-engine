"""DebateEval Benchmark -- test case definitions and benchmark runner.

Provides two suites:
    - **Regression suite** (10 cases): obvious defects for quick smoke tests.
    - **Benchmark suite** (15 cases): complex scenarios for quantitative results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .metrics import (
    DebateEvalScores,
    MetricName,
    MetricResult,
    compute_bdr,
    compute_ce,
    compute_cv,
    compute_far,
    compute_hd,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BenchmarkCase data structure
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkCase:
    """A single benchmark test case.

    Attributes:
        id: Unique identifier (e.g. ``"reg-code-001"``).
        name: Human-readable name.
        task_type: ``CODE_REVIEW``, ``RAG_VALIDATION``, or ``ARCHITECTURE_DECISION``.
        content: Input content to critique.
        gold_standard_defects: Known defects for BDR/FAR evaluation.
        reference_answer: Optional reference for CV metric.
        baseline_answer: Optional single-agent answer for HD metric.
        expected_bdr: Expected BDR for regression assertions.
        is_regression: ``True`` for quick regression tests.
    """

    id: str
    name: str
    task_type: str
    content: str
    gold_standard_defects: list[dict] = field(default_factory=list)
    reference_answer: str | None = None
    baseline_answer: str | None = None
    expected_bdr: float | None = None
    is_regression: bool = False


# ---------------------------------------------------------------------------
# BenchmarkResult
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Aggregated results from a benchmark run.

    Attributes:
        suite_name: Name of the suite (``"regression"`` or ``"benchmark"``).
        total_cases: Number of cases in the suite.
        passed: Number of cases that met their expected thresholds.
        failed: Number of cases that did not meet thresholds.
        scores: Per-case evaluation scores.
        aggregate_scores: Averaged scores across all cases.
        details: Additional metadata.
    """

    suite_name: str
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    scores: dict[str, DebateEvalScores] = field(default_factory=dict)
    aggregate_scores: DebateEvalScores = field(default_factory=DebateEvalScores)
    details: dict = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable summary of the benchmark run."""
        lines = [
            f"Benchmark Suite: {self.suite_name}",
            f"  Total: {self.total_cases}  Passed: {self.passed}  Failed: {self.failed}",
            "",
            "Aggregate Scores:",
        ]
        for m in self.aggregate_scores.metrics:
            lines.append(f"  {m.name.value:30s} = {m.value:.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# BenchmarkSuite
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkSuite:
    """A named collection of benchmark cases."""

    name: str
    cases: list[BenchmarkCase] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 10 REGRESSION test cases (obvious defects, BDR should be 1.0)
# ---------------------------------------------------------------------------

REGRESSION_CASES: list[BenchmarkCase] = [
    # -- Code Review (6 cases) --
    BenchmarkCase(
        id="reg-code-001",
        name="SQL Injection Vulnerability",
        task_type="CODE_REVIEW",
        content="""```python
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route('/user')
def get_user():
    user_id = request.args.get('id')
    conn = sqlite3.connect('users.db')
    cursor = conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
    result = cursor.fetchall()
    conn.close()
    return str(result)
```""",
        gold_standard_defects=[
            {
                "description": "SQL injection vulnerability via unsanitized user input",
                "defect_type": "SECURITY_RISK",
                "target_area": "database query",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-code-002",
        name="Plaintext Password Storage",
        task_type="CODE_REVIEW",
        content="""```python
import hashlib

def store_user(username, password):
    hashed = hashlib.md5(password.encode()).hexdigest()
    db.execute("INSERT INTO users VALUES (?, ?)", (username, hashed))
```""",
        gold_standard_defects=[
            {
                "description": "MD5 is cryptographically broken for password hashing",
                "defect_type": "SECURITY_RISK",
                "target_area": "password hashing",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-code-003",
        name="Hardcoded API Key",
        task_type="CODE_REVIEW",
        content="""```python
import requests

API_KEY = "sk-1234567890abcdef1234567890abcdef"

def fetch_data(user_id):
    resp = requests.get(
        f"https://api.example.com/users/{user_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    return resp.json()
```""",
        gold_standard_defects=[
            {
                "description": "Hardcoded API secret key in source code",
                "defect_type": "SECURITY_RISK",
                "target_area": "credential management",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-code-004",
        name="Unhandled Exception in Loop",
        task_type="CODE_REVIEW",
        content="""```python
def process_files(filenames):
    results = []
    for f in filenames:
        data = open(f).read()
        results.append(data.upper())
    return results
```""",
        gold_standard_defects=[
            {
                "description": "File handle is never closed, causing resource leak",
                "defect_type": "PERFORMANCE_ISSUE",
                "target_area": "file I/O",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-code-005",
        name="Race Condition in Counter",
        task_type="CODE_REVIEW",
        content="""```python
import threading

class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
```""",
        gold_standard_defects=[
            {
                "description": (
                    "Non-atomic counter increment causes race condition "
                    "in threaded context"
                ),
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "thread safety",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-code-006",
        name="Insecure Deserialization",
        task_type="CODE_REVIEW",
        content="""```python
import pickle

def load_session(data):
    return pickle.loads(data)
```""",
        gold_standard_defects=[
            {
                "description": "pickle.loads on untrusted data enables arbitrary code execution",
                "defect_type": "SECURITY_RISK",
                "target_area": "deserialization",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    # -- RAG Validation (4 cases) --
    BenchmarkCase(
        id="reg-rag-001",
        name="Fabricated Citation",
        task_type="RAG_VALIDATION",
        content="""Based on the retrieved documents, the Eiffel Tower was completed in 1887
and was designed by Gustav Eiffel. According to Smith et al. (2023), the tower
receives over 10 million visitors annually.""",
        gold_standard_defects=[
            {
                "description": "The Eiffel Tower was completed in 1889, not 1887",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "historical date",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-rag-002",
        name="Contradicts Retrieved Context",
        task_type="RAG_VALIDATION",
        content="""The retrieved context states that Python 3.12 was released in October 2023.
Based on this, Python 3.12 was released in December 2023.""",
        gold_standard_defects=[
            {
                "description": "Answer contradicts the retrieved context about the release date",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "factual consistency",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-rag-003",
        name="Hallucinated Statistic",
        task_type="RAG_VALIDATION",
        content="""According to the provided documents, JavaScript is used by 98.5% of all
websites as of 2024. This makes it the most popular programming language
for client-side web development.""",
        gold_standard_defects=[
            {
                "description": "The 98.5% statistic is not present in the retrieved documents and is fabricated",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "statistical claim",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
    BenchmarkCase(
        id="reg-rag-004",
        name="Missing Source Attribution",
        task_type="RAG_VALIDATION",
        content="""The company was founded in 2015 and has grown to over 500 employees.
Their main product uses machine learning for fraud detection.""",
        gold_standard_defects=[
            {
                "description": "Claims are presented without any source attribution from retrieved documents",
                "defect_type": "UNSUPPORTED_ASSUMPTION",
                "target_area": "source attribution",
            },
        ],
        expected_bdr=1.0,
        is_regression=True,
    ),
]


# ---------------------------------------------------------------------------
# 15 BENCHMARK test cases (more complex, for quantitative results)
# ---------------------------------------------------------------------------

BENCHMARK_CASES: list[BenchmarkCase] = [
    # -- Code Review: Medium Complexity (3 cases) --
    BenchmarkCase(
        id="bench-code-001",
        name="N+1 Query Pattern",
        task_type="CODE_REVIEW",
        content="""```python
from sqlalchemy.orm import Session

def get_users_with_posts(db: Session):
    users = db.query(User).all()
    result = []
    for user in users:
        posts = db.query(Post).filter(Post.user_id == user.id).all()
        result.append({"user": user.name, "posts": len(posts)})
    return result
```""",
        gold_standard_defects=[
            {
                "description": "N+1 query pattern: executing a separate database query for each user in a loop",
                "defect_type": "PERFORMANCE_ISSUE",
                "target_area": "database queries",
            },
        ],
        reference_answer="Use a joined query or selectinload to fetch users and posts in a single query.",
    ),
    BenchmarkCase(
        id="bench-code-002",
        name="Missing Input Validation",
        task_type="CODE_REVIEW",
        content="""```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/transfer")
def transfer_money(from_account: str, to_account: str, amount: float):
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    # perform transfer
    return {"status": "ok"}
```""",
        gold_standard_defects=[
            {
                "description": "No validation that from_account and to_account exist or are different",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "input validation",
            },
            {
                "description": "No check for sufficient balance before transfer",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "business logic",
            },
        ],
        reference_answer="Validate account existence, ensure accounts differ, and check sufficient balance.",
    ),
    BenchmarkCase(
        id="bench-code-003",
        name="Improper Error Handling",
        task_type="CODE_REVIEW",
        content="""```python
import json

def load_config(path):
    with open(path) as f:
        data = json.load(f)
    return data["database"]["host"]
```""",
        gold_standard_defects=[
            {
                "description": "No error handling for file not found or invalid JSON",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "error handling",
            },
            {
                "description": "No check that 'database' or 'host' keys exist in the config",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "key access",
            },
        ],
        reference_answer="Add try/except for file and JSON errors, validate required keys exist.",
    ),
    # -- Code Review: High Complexity (3 cases) --
    BenchmarkCase(
        id="bench-code-004",
        name="Thread-Safe Singleton with Double-Checked Locking",
        task_type="CODE_REVIEW",
        content="""```python
import threading

class Singleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.value = 42
        self._initialized = True
```""",
        gold_standard_defects=[
            {
                "description": "Double-checked locking pattern in Python is unreliable due to the GIL and object creation semantics",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "thread safety",
            },
            {
                "description": "The _initialized flag is set as instance attribute but checked before __new__ returns the instance",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "initialization logic",
            },
        ],
        reference_answer="Use a module-level singleton or functools.lru_cache for simpler, correct implementation.",
    ),
    BenchmarkCase(
        id="bench-code-005",
        name="Async Function Blocking Event Loop",
        task_type="CODE_REVIEW",
        content="""```python
import asyncio
import requests

async def fetch_all(urls: list[str]) -> list[str]:
    results = []
    for url in urls:
        resp = requests.get(url)
        results.append(resp.text)
    return results
```""",
        gold_standard_defects=[
            {
                "description": "Synchronous requests.get blocks the async event loop, defeating concurrency",
                "defect_type": "PERFORMANCE_ISSUE",
                "target_area": "async implementation",
            },
            {
                "description": "Requests are sequential despite the async function signature",
                "defect_type": "PERFORMANCE_ISSUE",
                "target_area": "concurrency",
            },
        ],
        reference_answer="Use aiohttp or httpx async client with asyncio.gather for concurrent requests.",
    ),
    BenchmarkCase(
        id="bench-code-006",
        name="Memory Leak in Caching",
        task_type="CODE_REVIEW",
        content="""```python
_cache = {}

def get_result(key: str, compute_fn):
    if key not in _cache:
        _cache[key] = compute_fn(key)
    return _cache[key]
```""",
        gold_standard_defects=[
            {
                "description": "Unbounded cache grows without limit, causing memory leak over time",
                "defect_type": "PERFORMANCE_ISSUE",
                "target_area": "memory management",
            },
            {
                "description": "No cache eviction policy or size limit",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "cache design",
            },
        ],
        reference_answer="Use functools.lru_cache or an LRU cache with a max size limit.",
    ),
    # -- RAG Validation: Low Hallucination (2 cases) --
    BenchmarkCase(
        id="bench-rag-001",
        name="Accurate Summary",
        task_type="RAG_VALIDATION",
        content="""Based on the retrieved documents, the water cycle consists of evaporation,
condensation, precipitation, and collection. The sun drives evaporation from
oceans and other water bodies, forming water vapor that rises and cools to
form clouds.""",
        gold_standard_defects=[],
        reference_answer="The water cycle includes evaporation, condensation, precipitation, and collection, driven by solar energy.",
        baseline_answer="The water cycle is a process that moves water around the Earth.",
    ),
    BenchmarkCase(
        id="bench-rag-002",
        name="Well-Attributed Technical Answer",
        task_type="RAG_VALIDATION",
        content="""According to Document A, React was released by Facebook in 2013. Document B
confirms that React uses a virtual DOM for efficient UI updates. Both sources
agree that React's component-based architecture promotes code reuse.""",
        gold_standard_defects=[],
        reference_answer="React was created by Facebook in 2013, uses a virtual DOM, and follows component-based architecture.",
        baseline_answer="React is a JavaScript library for building user interfaces.",
    ),
    # -- RAG Validation: Medium Hallucination (2 cases) --
    BenchmarkCase(
        id="bench-rag-003",
        name="Partially Fabricated Answer",
        task_type="RAG_VALIDATION",
        content="""The retrieved documents describe Docker as a containerization platform released
in 2013 by Solomon Hykes. Docker uses namespaces and cgroups for isolation.
Docker Desktop has been downloaded over 100 million times according to the
2024 developer survey.""",
        gold_standard_defects=[
            {
                "description": "The 100 million download claim is not supported by the retrieved documents",
                "defect_type": "UNSUPPORTED_ASSUMPTION",
                "target_area": "statistical claim",
            },
        ],
        reference_answer="Docker is a containerization platform from 2013 using namespaces and cgroups.",
        baseline_answer="Docker is a tool for running containers.",
    ),
    BenchmarkCase(
        id="bench-rag-004",
        name="Mixed Accuracy with One Error",
        task_type="RAG_VALIDATION",
        content="""Based on the context, Kubernetes was originally developed at Google and was
released as open source in 2014. It is written in Go and uses etcd for state
storage. Kubernetes supports automatic binary deployment of containers.""",
        gold_standard_defects=[
            {
                "description": "Kubernetes supports automatic binary deployment is incorrect; it uses declarative YAML manifests",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "deployment mechanism",
            },
        ],
        reference_answer="Kubernetes was developed at Google, open-sourced in 2014, written in Go, uses etcd.",
        baseline_answer="Kubernetes is a container orchestration platform.",
    ),
    # -- RAG Validation: High Hallucination (2 cases) --
    BenchmarkCase(
        id="bench-rag-005",
        name="Mostly Fabricated Answer",
        task_type="RAG_VALIDATION",
        content="""According to the documents, the Great Wall of China was built in a single
decade by Emperor Qin Shi Huang. It stretches over 50,000 kilometers and
was primarily built to protect against Mongol invasions from the north.
The wall is visible from space with the naked eye.""",
        gold_standard_defects=[
            {
                "description": "The Great Wall was built over many centuries, not a single decade",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "historical accuracy",
            },
            {
                "description": "The 50,000 km figure is incorrect; the actual length is approximately 21,000 km",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "factual accuracy",
            },
            {
                "description": "The claim that the wall is visible from space is a well-known myth",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "common misconception",
            },
        ],
        reference_answer="The Great Wall was built over many dynasties, is about 21,000 km long, and cannot be seen from space.",
        baseline_answer="The Great Wall of China is a famous historical landmark.",
    ),
    BenchmarkCase(
        id="bench-rag-006",
        name="Confident but Wrong Answer",
        task_type="RAG_VALIDATION",
        content="""The documents clearly state that the speed of light is approximately 300,000
km/s in a vacuum. However, in water, light travels at 600,000 km/s, which is
twice as fast. This is because water has a lower refractive index than air.""",
        gold_standard_defects=[
            {
                "description": "Light travels slower in water, not faster; the speed is approximately 225,000 km/s",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "physics accuracy",
            },
            {
                "description": "Water has a higher refractive index than air, not lower",
                "defect_type": "FACTUAL_ERROR",
                "target_area": "scientific accuracy",
            },
        ],
        reference_answer="Light travels slower in water (~225,000 km/s) due to higher refractive index.",
        baseline_answer="Light travels at different speeds in different media.",
    ),
    # -- Architecture Decision (3 cases, for CS ablation) --
    BenchmarkCase(
        id="bench-arch-001",
        name="Monolith vs Microservices",
        task_type="ARCHITECTURE_DECISION",
        content="""Proposal: Migrate our e-commerce platform from a monolithic architecture to
microservices. We will split the monolith into 15 independent services
communicating via REST APIs. Each service will have its own database.
We plan to complete the migration in 3 months with a team of 4 developers.""",
        gold_standard_defects=[
            {
                "description": "Splitting into 15 services for a 4-person team creates excessive operational overhead",
                "defect_type": "SCALABILITY_CONCERN",
                "target_area": "team capacity",
            },
            {
                "description": "3-month timeline is unrealistic for a full monolith-to-microservices migration",
                "defect_type": "UNSUPPORTED_ASSUMPTION",
                "target_area": "timeline estimation",
            },
            {
                "description": "No mention of service discovery, API gateway, or distributed tracing infrastructure",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "infrastructure planning",
            },
        ],
        reference_answer="Start with a strangler fig pattern, extract 2-3 services first, invest in observability infrastructure.",
    ),
    BenchmarkCase(
        id="bench-arch-002",
        name="Database Technology Choice",
        task_type="ARCHITECTURE_DECISION",
        content="""Proposal: Replace our PostgreSQL database with MongoDB for all data storage.
NoSQL is more modern and scalable. We will store user profiles, transactions,
and analytics all in the same MongoDB cluster. Schema design will be done
after migration to take advantage of schema flexibility.""",
        gold_standard_defects=[
            {
                "description": "Transaction data requires ACID guarantees that MongoDB provides only with additional configuration",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "data integrity",
            },
            {
                "description": "Deferring schema design until after migration is a risky approach",
                "defect_type": "UNSUPPORTED_ASSUMPTION",
                "target_area": "planning",
            },
            {
                "description": "Using a single database type for all workloads ignores different access patterns",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "workload analysis",
            },
        ],
        reference_answer="Use polyglot persistence: PostgreSQL for transactions, MongoDB for documents, time-series DB for analytics.",
    ),
    BenchmarkCase(
        id="bench-arch-003",
        name="Caching Strategy",
        task_type="ARCHITECTURE_DECISION",
        content="""Proposal: Implement caching by adding Redis in front of every database query.
All queries will be cached for 24 hours. Cache invalidation will be handled
by setting TTL only. We expect this to reduce database load by 100%.""",
        gold_standard_defects=[
            {
                "description": "24-hour TTL for all queries risks serving stale data, especially for mutable data",
                "defect_type": "LOGICAL_FALLACY",
                "target_area": "cache invalidation",
            },
            {
                "description": "100% database load reduction is unrealistic; cache misses and writes still hit the database",
                "defect_type": "UNSUPPORTED_ASSUMPTION",
                "target_area": "performance expectation",
            },
            {
                "description": "No differentiation between cacheable read-heavy and non-cacheable write-heavy queries",
                "defect_type": "MISSING_CONSIDERATION",
                "target_area": "query analysis",
            },
        ],
        reference_answer="Cache read-heavy, rarely-changing data with shorter TTLs. Use cache-aside pattern with selective invalidation.",
    ),
]


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------


class BenchmarkRunner:
    """Run benchmark suites against DebateEngine.

    Parameters
    ----------
    engine:
        A :class:`QuickCritiqueEngine` instance (or any object with an
        async ``critique`` method).
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def run_single(self, case: BenchmarkCase) -> dict:
        """Run a single benchmark case through the engine.

        Returns a dict with keys ``case_id``, ``case_name``, ``consensus``,
        ``eval_scores``, and ``passed`` (for regression cases).
        """
        from ..schemas.config import CritiqueConfigSchema

        config = CritiqueConfigSchema(
            content=case.content,
            task_type=case.task_type,
        )

        consensus = await self.engine.critique(config)

        # Extract discovered defects from consensus
        discovered = self._extract_defects(consensus)

        # Compute metrics
        scores = DebateEvalScores()
        scores.add(compute_bdr(discovered, case.gold_standard_defects))
        scores.add(compute_far(discovered, case.gold_standard_defects))

        if case.reference_answer:
            scores.add(compute_cv(consensus.final_conclusion, case.reference_answer))

        if case.baseline_answer and case.reference_answer:
            debate_faithfulness = _keyword_overlap_score(
                consensus.final_conclusion, case.reference_answer
            )
            baseline_faithfulness = _keyword_overlap_score(
                case.baseline_answer, case.reference_answer
            )
            scores.add(compute_hd(debate_faithfulness, baseline_faithfulness))

        # Cost and rounds from metadata
        rounds = getattr(consensus.debate_metadata, "rounds_completed", 1)
        cost = getattr(consensus.debate_metadata, "total_cost_usd", 0.0)
        cv_result = scores.get(MetricName.CV)
        if cv_result is not None:
            scores.add(compute_ce(cv_result.value, rounds, cost))

        # Check regression
        passed = True
        if case.is_regression and case.expected_bdr is not None:
            bdr_result = scores.get(MetricName.BDR)
            if bdr_result is not None:
                passed = bdr_result.value >= case.expected_bdr

        return {
            "case_id": case.id,
            "case_name": case.name,
            "consensus": consensus,
            "eval_scores": scores,
            "passed": passed,
        }

    async def run_regression(self) -> list[dict]:
        """Run all 10 regression cases.

        Returns a list of result dicts (one per case).
        """
        results: list[dict] = []
        for case in REGRESSION_CASES:
            logger.info("Running regression case: %s (%s)", case.id, case.name)
            try:
                result = await self.run_single(case)
                results.append(result)
                status = "PASS" if result["passed"] else "FAIL"
                logger.info("  %s: %s", case.id, status)
            except Exception as exc:
                logger.error("  %s: ERROR - %s", case.id, exc)
                results.append(
                    {
                        "case_id": case.id,
                        "case_name": case.name,
                        "consensus": None,
                        "eval_scores": None,
                        "passed": False,
                        "error": str(exc),
                    }
                )
        return results

    async def run_benchmark(self) -> BenchmarkResult:
        """Run all 15 benchmark cases and return aggregated results.

        Returns a :class:`BenchmarkResult` with per-case and aggregate scores.
        """
        result = BenchmarkResult(suite_name="benchmark", total_cases=len(BENCHMARK_CASES))

        # Collect per-metric sums for aggregation
        metric_sums: dict[str, list[float]] = {}

        for case in BENCHMARK_CASES:
            logger.info("Running benchmark case: %s (%s)", case.id, case.name)
            try:
                case_result = await self.run_single(case)
                scores: DebateEvalScores | None = case_result["eval_scores"]
                if scores is not None:
                    result.scores[case.id] = scores
                    for m in scores.metrics:
                        metric_sums.setdefault(m.name.value, []).append(m.value)
                if case_result["passed"]:
                    result.passed += 1
                else:
                    result.failed += 1
            except Exception as exc:
                logger.error("  %s: ERROR - %s", case.id, exc)
                result.failed += 1

        # Compute aggregates
        for metric_name, values in metric_sums.items():
            avg = sum(values) / len(values) if values else 0.0
            result.aggregate_scores.add(
                MetricResult(
                    name=MetricName(metric_name),
                    value=round(avg, 4),
                    description=f"Average {metric_name} across {len(values)} cases.",
                    details={"case_count": len(values), "std_dev": round(self._std_dev(values), 4)},
                )
            )

        return result

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_defects(consensus: Any) -> list[dict]:
        """Extract defect dicts from a ConsensusSchema.

        Pulls from ``critiques_summary`` and ``adopted_contributions``.
        """
        defects: list[dict] = []

        # From critiques_summary
        for critique in getattr(consensus, "critiques_summary", []):
            defect = {
                "description": getattr(critique, "evidence", ""),
                "defect_type": getattr(critique, "defect_type", "GENERAL"),
                "target_area": getattr(critique, "target_area", ""),
            }
            # Normalise defect_type to string
            dt = defect["defect_type"]
            defect["defect_type"] = dt.value if hasattr(dt, "value") else str(dt)
            defects.append(defect)

        return defects

    @staticmethod
    def _std_dev(values: list[float]) -> float:
        """Compute population standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance**0.5


# ---------------------------------------------------------------------------
# Convenience: re-export keyword_overlap_score for HD baseline computation
# ---------------------------------------------------------------------------

from .metrics import _keyword_overlap_score  # noqa: E402 (needed by runner)
