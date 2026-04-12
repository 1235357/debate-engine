"""Tests for the DebateEval evaluation framework.

Covers all 7 metrics, the DebateEvalScores container, BenchmarkCase
data structures, and the DebateEvaluator orchestrator.

"""

from __future__ import annotations

import pytest

from debate_engine.eval.metrics import (
    DebateEvalScores,
    MetricName,
    MetricResult,
    compute_bdr,
    compute_ce,
    compute_cis,
    compute_cv,
    compute_far,
    compute_hd,
    compute_rd,
)
from debate_engine.eval.benchmark import (
    BENCHMARK_CASES,
    REGRESSION_CASES,
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkSuite,
)
from debate_engine.eval.evaluator import DebateEvaluator


# ===================================================================
# Helpers
# ===================================================================

def _make_defect(description: str, defect_type: str = "SECURITY_RISK", target_area: str = "code") -> dict:
    return {"description": description, "defect_type": defect_type, "target_area": target_area}


# ===================================================================
# MetricName enum
# ===================================================================

class TestMetricName:
    def test_all_values_exist(self):
        expected = {"bug_discovery_rate", "false_alarm_rate", "consensus_validity",
                     "conformity_impact_score", "convergence_efficiency", "reasoning_depth",
                     "hallucination_delta"}
        actual = {m.value for m in MetricName}
        assert actual == expected


# ===================================================================
# MetricResult dataclass
# ===================================================================

class TestMetricResult:
    def test_creation(self):
        mr = MetricResult(
            name=MetricName.BDR,
            value=0.85,
            description="Test metric",
            details={"key": "val"},
        )
        assert mr.name == MetricName.BDR
        assert mr.value == 0.85
        assert mr.description == "Test metric"
        assert mr.details == {"key": "val"}

    def test_default_details(self):
        mr = MetricResult(name=MetricName.FAR, value=0.1, description="Test")
        assert mr.details == {}


# ===================================================================
# DebateEvalScores container
# ===================================================================

class TestDebateEvalScores:
    def test_add_and_get(self):
        scores = DebateEvalScores()
        m = MetricResult(name=MetricName.BDR, value=0.9, description="BDR test")
        scores.add(m)
        assert scores.get(MetricName.BDR) is m
        assert scores.get(MetricName.FAR) is None

    def test_to_dict(self):
        scores = DebateEvalScores()
        scores.add(MetricResult(name=MetricName.BDR, value=0.8, description="desc"))
        d = scores.to_dict()
        assert "bug_discovery_rate" in d
        assert d["bug_discovery_rate"]["value"] == 0.8
        assert d["bug_discovery_rate"]["description"] == "desc"

    def test_summary(self):
        scores = DebateEvalScores()
        scores.add(MetricResult(name=MetricName.BDR, value=1.0, description="Perfect recall"))
        s = scores.summary()
        assert "bug_discovery_rate" in s
        assert "1.0000" in s
        assert "Perfect recall" in s

    def test_empty_summary(self):
        scores = DebateEvalScores()
        s = scores.summary()
        assert "no metrics recorded" in s

    def test_repr(self):
        scores = DebateEvalScores()
        scores.add(MetricResult(name=MetricName.BDR, value=0.5, description=""))
        r = repr(scores)
        assert "bug_discovery_rate" in r


# ===================================================================
# BDR (Bug Discovery Rate)
# ===================================================================

class TestBDR:
    def test_perfect_recall(self):
        """All gold defects discovered."""
        gold = [_make_defect("SQL injection vulnerability in query")]
        discovered = [_make_defect("SQL injection vulnerability in the database query")]
        result = compute_bdr(discovered, gold)
        assert result.name == MetricName.BDR
        assert result.value == 1.0

    def test_partial_recall(self):
        """Only some gold defects discovered."""
        gold = [
            _make_defect("SQL injection vulnerability in query"),
            _make_defect("Missing input validation on form fields"),
        ]
        discovered = [_make_defect("SQL injection vulnerability in database query")]
        result = compute_bdr(discovered, gold)
        assert result.value == 0.5

    def test_zero_recall(self):
        """No gold defects discovered."""
        gold = [_make_defect("Buffer overflow in memory allocation")]
        discovered = [_make_defect("Code style issue with indentation")]
        result = compute_bdr(discovered, gold)
        assert result.value == 0.0

    def test_empty_gold(self):
        """No gold defects -- vacuously true."""
        result = compute_bdr([_make_defect("something")], [])
        assert result.value == 1.0

    def test_empty_discovered(self):
        """Nothing discovered but gold exists."""
        gold = [_make_defect("SQL injection vulnerability")]
        result = compute_bdr([], gold)
        assert result.value == 0.0

    def test_details_structure(self):
        gold = [_make_defect("SQL injection")]
        discovered = [_make_defect("SQL injection vulnerability")]
        result = compute_bdr(discovered, gold)
        assert "true_positives" in result.details
        assert "gold_count" in result.details
        assert "discovered_count" in result.details


# ===================================================================
# FAR (False Alarm Rate)
# ===================================================================

class TestFAR:
    def test_no_false_alarms(self):
        """All discovered defects match gold."""
        gold = [_make_defect("SQL injection vulnerability")]
        discovered = [_make_defect("SQL injection vulnerability in query")]
        result = compute_far(discovered, gold)
        assert result.name == MetricName.FAR
        assert result.value == 0.0

    def test_some_false_alarms(self):
        """Some discovered defects don't match gold."""
        gold = [_make_defect("SQL injection vulnerability")]
        discovered = [
            _make_defect("SQL injection vulnerability"),
            _make_defect("Code formatting issue with spaces"),
        ]
        result = compute_far(discovered, gold)
        assert result.value == 0.5

    def test_all_false_alarms(self):
        """None of the discovered defects match gold."""
        gold = [_make_defect("SQL injection vulnerability")]
        discovered = [_make_defect("Naming convention violation")]
        result = compute_far(discovered, gold)
        assert result.value == 1.0

    def test_empty_discovered(self):
        """No discoveries means no false alarms."""
        result = compute_far([], [_make_defect("something")])
        assert result.value == 0.0

    def test_empty_gold(self):
        """No gold standard -- everything is a false alarm."""
        discovered = [_make_defect("something")]
        result = compute_far(discovered, [])
        assert result.value == 1.0


# ===================================================================
# CV (Consensus Validity)
# ===================================================================

class TestCV:
    def test_exact_match(self):
        """Identical text should yield high similarity."""
        text = "The code has a SQL injection vulnerability in the database query"
        result = compute_cv(text, text)
        assert result.name == MetricName.CV
        assert result.value == 1.0

    def test_partial_match(self):
        """Overlapping but not identical text."""
        consensus = "The code has a SQL injection vulnerability in the query"
        reference = "SQL injection vulnerability found in the database query string"
        result = compute_cv(consensus, reference)
        assert 0.0 < result.value < 1.0

    def test_no_match(self):
        """Completely unrelated text."""
        result = compute_cv("The sky is blue today", "Quantum physics explains particle behavior")
        assert result.value < 0.5

    def test_empty_strings(self):
        """Both empty should be 1.0 (vacuously similar)."""
        result = compute_cv("", "")
        assert result.value == 1.0


# ===================================================================
# CIS (Conformity Impact Score)
# ===================================================================

class TestCIS:
    def test_no_stance_changes(self):
        """CIS is 0.0 when there are no stance changes."""
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is good",
                "new_claim": "The code is good",
            },
        ]
        critiques = [{"severity": "CRITICAL", "target_role": "ROLE_A", "round": 1}]
        result = compute_cis(revision_history, critiques)
        assert result.name == MetricName.CIS
        assert result.value == 0.0

    def test_empty_history(self):
        """CIS is 0.0 when revision history is empty."""
        result = compute_cis([], [])
        assert result.value == 0.0

    def test_high_severity_driven_low_cis(self):
        """CIS close to 0.0 when stance changes are driven by high-severity critiques."""
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is perfectly secure",
                "new_claim": "The code has a critical SQL injection vulnerability",
                "adopted": True,
            },
        ]
        critiques = [
            {"severity": "CRITICAL", "target_role": "ROLE_A", "round": 1},
        ]
        result = compute_cis(revision_history, critiques)
        assert result.name == MetricName.CIS
        assert result.value == pytest.approx(0.0, abs=1e-4)

    def test_low_severity_driven_high_cis(self):
        """CIS close to 1.0 when stance changes are driven by low-severity critiques."""
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is perfectly secure",
                "new_claim": "The code has a critical SQL injection vulnerability",
                "adopted": True,
            },
        ]
        critiques = [
            {"severity": "MINOR", "target_role": "ROLE_A", "round": 1},
        ]
        result = compute_cis(revision_history, critiques)
        assert result.value == pytest.approx(1.0, abs=1e-4)

    def test_mixed_severity_moderate_cis(self):
        """CIS is moderate when mix of high and low severity critiques."""
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is secure",
                "new_claim": "The code has SQL injection vulnerability",
                "adopted": True,
            },
            {
                "round": 1,
                "role": "ROLE_B",
                "old_claim": "The code works fine",
                "new_claim": "The code needs refactoring",
                "adopted": True,
            },
        ]
        critiques = [
            {"severity": "CRITICAL", "target_role": "ROLE_A", "round": 1},
            {"severity": "MINOR", "target_role": "ROLE_B", "round": 1},
        ]
        result = compute_cis(revision_history, critiques)
        assert result.value == pytest.approx(0.5, abs=1e-4)

    def test_not_adopted_high_severity(self):
        """High-severity critique not adopted should not reduce CIS."""
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is secure",
                "new_claim": "The code has a vulnerability",
                "adopted": False,
            },
        ]
        critiques = [
            {"severity": "CRITICAL", "target_role": "ROLE_A", "round": 1},
        ]
        result = compute_cis(revision_history, critiques)
        assert result.value == pytest.approx(1.0, abs=1e-4)


# ===================================================================
# CE (Convergence Efficiency)
# ===================================================================

class TestCE:
    def test_normal_computation(self):
        result = compute_ce(cv_score=0.8, rounds_completed=2, total_cost_usd=0.05)
        assert result.name == MetricName.CE
        assert result.value == 8.0

    def test_zero_rounds(self):
        result = compute_ce(cv_score=0.8, rounds_completed=0, total_cost_usd=0.05)
        assert result.value == 0.0

    def test_zero_cost(self):
        result = compute_ce(cv_score=0.9, rounds_completed=2, total_cost_usd=0.0)
        assert result.value == 0.45

    def test_high_efficiency(self):
        result = compute_ce(cv_score=0.95, rounds_completed=1, total_cost_usd=0.01)
        assert result.value == 95.0


# ===================================================================
# RD (Reasoning Depth)
# ===================================================================

class TestRD:
    def test_all_concrete(self):
        """All critiques have concrete fixes."""
        critiques = [
            {"fix_kind": "CONCRETE_FIX"},
            {"fix_kind": "CONCRETE_FIX"},
            {"fix_kind": "CONCRETE_FIX"},
        ]
        result = compute_rd(critiques, adopted_count=2)
        assert result.name == MetricName.RD
        assert result.value == pytest.approx(2 / 3, abs=1e-4)

    def test_mixed_fix_kinds(self):
        critiques = [
            {"fix_kind": "CONCRETE_FIX"},
            {"fix_kind": "VALIDATION_STEP"},
            {"fix_kind": "NEED_MORE_DATA"},
        ]
        result = compute_rd(critiques, adopted_count=0)
        assert result.value == pytest.approx(1 / 3, abs=1e-4)

    def test_no_concrete_fixes(self):
        critiques = [
            {"fix_kind": "VALIDATION_STEP"},
            {"fix_kind": "NEED_MORE_DATA"},
        ]
        result = compute_rd(critiques)
        assert result.value == 0.0

    def test_empty_critiques(self):
        result = compute_rd([])
        assert result.value == 0.0

    def test_with_adoption(self):
        critiques = [
            {"fix_kind": "CONCRETE_FIX"},
            {"fix_kind": "CONCRETE_FIX"},
            {"fix_kind": "VALIDATION_STEP"},
            {"fix_kind": "NEED_MORE_DATA"},
        ]
        result = compute_rd(critiques, adopted_count=2)
        assert result.value == pytest.approx(0.5, abs=1e-4)


# ===================================================================
# HD (Hallucination Delta)
# ===================================================================

class TestHD:
    def test_positive_delta(self):
        """DebateEngine has fewer hallucinations than baseline."""
        result = compute_hd(debate_faithfulness=0.9, baseline_faithfulness=0.7)
        assert result.name == MetricName.HD
        assert result.value == pytest.approx(0.2, abs=1e-4)
        assert "fewer hallucinations" in result.description

    def test_negative_delta(self):
        """DebateEngine has more hallucinations than baseline."""
        result = compute_hd(debate_faithfulness=0.5, baseline_faithfulness=0.8)
        assert result.value == pytest.approx(-0.3, abs=1e-4)
        assert "more hallucinations" in result.description

    def test_zero_delta(self):
        """Same hallucination level."""
        result = compute_hd(debate_faithfulness=0.75, baseline_faithfulness=0.75)
        assert result.value == 0.0
        assert "same hallucination level" in result.description

    def test_details(self):
        result = compute_hd(0.85, 0.6)
        assert result.details["debate_faithfulness"] == 0.85
        assert result.details["baseline_faithfulness"] == 0.6


# ===================================================================
# BenchmarkCase data structure
# ===================================================================

class TestBenchmarkCase:
    def test_creation(self):
        case = BenchmarkCase(
            id="test-001",
            name="Test Case",
            task_type="CODE_REVIEW",
            content="print('hello')",
            gold_standard_defects=[_make_defect("debug statement")],
        )
        assert case.id == "test-001"
        assert case.name == "Test Case"
        assert case.task_type == "CODE_REVIEW"
        assert len(case.gold_standard_defects) == 1
        assert case.is_regression is False

    def test_regression_case(self):
        case = BenchmarkCase(
            id="reg-001",
            name="Regression",
            task_type="CODE_REVIEW",
            content="code",
            expected_bdr=1.0,
            is_regression=True,
        )
        assert case.is_regression is True
        assert case.expected_bdr == 1.0


# ===================================================================
# Benchmark suites
# ===================================================================

class TestBenchmarkSuites:
    def test_regression_suite_count(self):
        assert len(REGRESSION_CASES) == 10

    def test_benchmark_suite_count(self):
        assert len(BENCHMARK_CASES) == 15

    def test_regression_all_have_expected_bdr(self):
        for case in REGRESSION_CASES:
            assert case.expected_bdr is not None, f"{case.id} missing expected_bdr"
            assert case.is_regression, f"{case.id} not marked as regression"

    def test_regression_task_types(self):
        task_types = {c.task_type for c in REGRESSION_CASES}
        assert "CODE_REVIEW" in task_types
        assert "RAG_VALIDATION" in task_types

    def test_benchmark_task_types(self):
        task_types = {c.task_type for c in BENCHMARK_CASES}
        assert "CODE_REVIEW" in task_types
        assert "RAG_VALIDATION" in task_types
        assert "ARCHITECTURE_DECISION" in task_types

    def test_benchmark_result_summary(self):
        result = BenchmarkResult(suite_name="test", total_cases=5, passed=3, failed=2)
        s = result.summary()
        assert "test" in s
        assert "Total: 5" in s
        assert "Passed: 3" in s
        assert "Failed: 2" in s

    def test_benchmark_suite_dataclass(self):
        suite = BenchmarkSuite(
            name="custom",
            cases=[BenchmarkCase(id="c1", name="Case 1", task_type="CODE_REVIEW", content="x")],
        )
        assert suite.name == "custom"
        assert len(suite.cases) == 1


# ===================================================================
# DebateEvaluator
# ===================================================================

class TestDebateEvaluator:
    def _make_mock_consensus(
        self,
        conclusion: str = "The code has security vulnerabilities.",
        critiques_summary: list | None = None,
        rounds_completed: int = 1,
        total_cost_usd: float = 0.05,
    ):
        """Create a mock ConsensusSchema-like object."""
        from types import SimpleNamespace

        metadata = SimpleNamespace(
            rounds_completed=rounds_completed,
            total_cost_usd=total_cost_usd,
        )

        if critiques_summary is None:
            from debate_engine.schemas.enums import FixKind, Severity
            critiques_summary = [
                SimpleNamespace(
                    evidence="SQL injection vulnerability found in user query",
                    defect_type="SECURITY_RISK",
                    target_area="database query",
                    severity=Severity.CRITICAL,
                    fix_kind=FixKind.CONCRETE_FIX,
                    role_id="ROLE_A",
                ),
            ]

        return SimpleNamespace(
            final_conclusion=conclusion,
            critiques_summary=critiques_summary,
            debate_metadata=metadata,
            adopted_contributions={"ROLE_A": ["SQL injection fix adopted"]},
        )

    def test_evaluate_basic(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus()
        gold = [_make_defect("SQL injection vulnerability in database query")]
        scores = evaluator.evaluate(
            consensus=consensus,
            gold_standard=gold,
        )
        assert scores.get(MetricName.BDR) is not None
        assert scores.get(MetricName.FAR) is not None

    def test_evaluate_with_reference(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus(
            conclusion="The code has a SQL injection vulnerability in the database query"
        )
        gold = [_make_defect("SQL injection vulnerability")]
        scores = evaluator.evaluate(
            consensus=consensus,
            gold_standard=gold,
            reference_answer="SQL injection vulnerability found in the database query",
        )
        assert scores.get(MetricName.CV) is not None
        assert scores.get(MetricName.CE) is not None

    def test_evaluate_with_baseline(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus(
            conclusion="SQL injection vulnerability in the database query"
        )
        scores = evaluator.evaluate(
            consensus=consensus,
            gold_standard=[],
            reference_answer="SQL injection vulnerability found in database query",
            baseline_faithfulness=0.5,
        )
        assert scores.get(MetricName.HD) is not None

    def test_evaluate_with_revision_history(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus()
        revision_history = [
            {
                "round": 1,
                "role": "ROLE_A",
                "old_claim": "The code is secure",
                "new_claim": "The code has SQL injection vulnerability",
            },
        ]
        scores = evaluator.evaluate(
            consensus=consensus,
            gold_standard=[],
            revision_history=revision_history,
        )
        assert scores.get(MetricName.CIS) is not None

    def test_evaluate_empty_consensus(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus(
            conclusion="No issues found",
            critiques_summary=[],
        )
        scores = evaluator.evaluate(
            consensus=consensus,
            gold_standard=[_make_defect("SQL injection")],
        )
        bdr = scores.get(MetricName.BDR)
        assert bdr is not None
        assert bdr.value == 0.0

    def test_evaluate_returns_scores_object(self):
        evaluator = DebateEvaluator()
        consensus = self._make_mock_consensus()
        scores = evaluator.evaluate(consensus=consensus, gold_standard=[])
        assert isinstance(scores, DebateEvalScores)
        assert len(scores.metrics) > 0
        d = scores.to_dict()
        assert isinstance(d, dict)


# ===================================================================
# Integration: full pipeline with keyword matching
# ===================================================================

class TestIntegration:
    def test_bdr_far_consistency(self):
        """BDR and FAR should be computed consistently on the same data."""
        gold = [
            _make_defect("SQL injection vulnerability in query"),
            _make_defect("Missing error handling for file operations"),
        ]
        discovered = [
            _make_defect("SQL injection vulnerability in database query"),
            _make_defect("Code style issue with variable naming"),
        ]
        bdr = compute_bdr(discovered, gold)
        far = compute_far(discovered, gold)
        assert bdr.value == 0.5
        assert far.value == 0.5

    def test_all_metrics_on_realistic_data(self):
        """Run all metrics on a realistic scenario."""
        gold = [_make_defect("SQL injection vulnerability in user input query")]
        discovered = [_make_defect("SQL injection vulnerability in user query")]
        consensus_text = "The code contains a SQL injection vulnerability in the user input query"
        reference = "SQL injection vulnerability found in user input query"

        scores = DebateEvalScores()
        scores.add(compute_bdr(discovered, gold))
        scores.add(compute_far(discovered, gold))
        scores.add(compute_cv(consensus_text, reference))
        scores.add(compute_ce(0.9, 2, 0.04))
        scores.add(compute_hd(0.85, 0.6))
        scores.add(compute_rd(
            [{"fix_kind": "CONCRETE_FIX"}, {"fix_kind": "VALIDATION_STEP"}],
            adopted_count=1,
        ))
        scores.add(compute_cis(
            revision_history=[{
                "round": 1, "role": "ROLE_A",
                "old_claim": "Code is secure",
                "new_claim": "Code has SQL injection vulnerability",
                "adopted": True,
            }],
            critiques=[{"severity": "CRITICAL", "target_role": "ROLE_A", "round": 1}],
        ))

        assert len(scores.metrics) == 7
        assert scores.get(MetricName.BDR).value == 1.0
        assert scores.get(MetricName.FAR).value == 0.0
        assert scores.get(MetricName.HD).value > 0

        summary = scores.summary()
        for m in MetricName:
            assert m.value in summary
