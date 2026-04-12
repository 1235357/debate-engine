"""DebateEval -- evaluation framework for DebateEngine.

This package provides metrics, benchmarks, and evaluation tooling for
measuring the quality of multi-agent critique and consensus outputs.

Exports:
    DebateEvaluator: Main evaluation orchestrator.
    DebateEvalScores: Container for evaluation metric results.
    BenchmarkResult: Aggregated benchmark run results.
    BenchmarkSuite: A named collection of benchmark cases.
"""

from .evaluator import DebateEvaluator
from .metrics import DebateEvalScores, MetricName, MetricResult
from .benchmark import BenchmarkCase, BenchmarkResult, BenchmarkSuite, BenchmarkRunner

__all__ = [
    "DebateEvaluator",
    "DebateEvalScores",
    "MetricName",
    "MetricResult",
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkSuite",
    "BenchmarkRunner",
]