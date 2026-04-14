"""CLI tests for DebateEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from debate_engine.cli import main


def test_cli_help():
    """Test the CLI help command."""
    with patch('sys.argv', ['debate-engine', '--help']), \
         patch('argparse.ArgumentParser.print_help') as mock_help:
        try:
            main()
        except SystemExit:
            pass
        mock_help.assert_called_once()


def test_cli_version():
    """Test the CLI version command."""
    with patch('sys.argv', ['debate-engine', '--version']), \
         patch('builtins.print') as mock_print, \
         patch('debate_engine.__version__', '1.0.0'):
        try:
            main()
        except SystemExit:
            pass
        mock_print.assert_called_once_with('debate-engine version 1.0.0')


@patch("debate_engine.cli.QuickCritiqueEngine")
def test_cli_critique(mock_engine_class):
    """Test the CLI critique command."""
    # Mock the engine with AsyncMock for the critique method
    mock_engine = mock_engine_class.return_value
    mock_engine.critique = AsyncMock(return_value=MagicMock(
        final_conclusion='Test conclusion',
        consensus_confidence=0.85,
        critiques_summary=[],
        debate_metadata=MagicMock(
            request_id='test-request-id',
            task_type=MagicMock(value='CODE_REVIEW'),
            provider_mode=MagicMock(value='STABLE'),
            rounds_completed=1,
            total_cost_usd=0.05,
            total_latency_ms=1000.0,
            models_used=['test-model'],
            quorum_achieved=True,
            termination_reason=MagicMock(value='COMPLETED'),
            parse_attempts_total=0
        ),
        adopted_contributions={},
        rejected_positions=[],
        remaining_disagreements=[],
        disagreement_confirmation='',
        preserved_minority_opinions=[],
        partial_return=False
    ))

    # Test the critique command
    with patch('sys.argv', [
        'debate-engine', 'critique',
        '--content', 'def hello(): print(\'hello\')',
        '--task-type', 'CODE_REVIEW'
    ]), \
         patch('builtins.print') as mock_print:
        try:
            main()
        except SystemExit:
            pass

        # Check that print was called with the expected output
        mock_print.assert_any_call('Conclusion: Test conclusion')
        mock_print.assert_any_call('Confidence: 85%')
        # Check that the critique method was called
        mock_engine.critique.assert_called_once()
