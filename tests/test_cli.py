"""CLI tests for DebateEngine."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch


def test_cli_help():
    """Test the CLI help command."""
    result = subprocess.run(
        [sys.executable, "-m", "debate_engine", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "debate-engine" in result.stdout


def test_cli_version():
    """Test the CLI version command."""
    result = subprocess.run(
        [sys.executable, "-m", "debate_engine", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "version" in result.stdout


@patch("debate_engine.cli.QuickCritiqueEngine")
def test_cli_critique(mock_engine_class):
    """Test the CLI critique command."""
    # Mock the engine
    mock_engine = mock_engine_class.return_value
    mock_engine.critique.return_value = type('MockConsensus', (), {
        'final_conclusion': 'Test conclusion',
        'consensus_confidence': 0.85,
        'critiques_summary': [],
        'debate_metadata': type('MockMetadata', (), {
            'request_id': 'test-request-id',
            'task_type': type('MockEnum', (), {'value': 'CODE_REVIEW'}),
            'provider_mode': type('MockEnum', (), {'value': 'STABLE'}),
            'rounds_completed': 1,
            'total_cost_usd': 0.05,
            'total_latency_ms': 1000.0,
            'models_used': ['test-model'],
            'quorum_achieved': True,
            'termination_reason': type('MockEnum', (), {'value': 'COMPLETED'}),
            'parse_attempts_total': 0
        })(),
        'adopted_contributions': {},
        'rejected_positions': [],
        'remaining_disagreements': [],
        'disagreement_confirmation': '',
        'preserved_minority_opinions': [],
        'partial_return': False
    })()

    # Test the critique command
    result = subprocess.run(
        [
            sys.executable, "-m", "debate_engine", "critique",
            "--content", "def hello(): print('hello')",
            "--task-type", "CODE_REVIEW"
        ],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "Test conclusion" in result.stdout
    assert "Confidence: 85%" in result.stdout
