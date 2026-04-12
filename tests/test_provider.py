"""Tests for the LLM provider layer.

All LLM calls are mocked to test provider selection, retry logic,
JSON parsing, cost tracking, and timeout handling.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debate_engine.providers.config import ProviderConfig, ProviderEntry, ProviderMode
from debate_engine.providers.llm_provider import CallResult, LLMProvider


# ===================================================================
# ProviderConfig.from_env tests
# ===================================================================


class TestProviderConfigFromEnv:
    """Test environment variable loading for ProviderConfig."""

    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEBATE_ENGINE_MODE", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_PROVIDER", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_MODEL", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_BACKUP_PROVIDER", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_BACKUP_MODEL", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_JUDGE_MODEL", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_TIMEOUT", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_MAX_TRANSPORT_RETRIES", raising=False)
        monkeypatch.delenv("DEBATE_ENGINE_MAX_PARSE_RETRIES", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = ProviderConfig.from_env()
        assert config.primary_provider == "openai"
        assert config.primary_model == "gpt-4o-mini"
        assert config.mode == ProviderMode.STABLE
        assert config.timeout_seconds == 25.0
        assert config.max_transport_retries == 2
        assert config.max_parse_retries == 1
        assert config.backup_provider is None
        assert config.backup_model is None

    def test_from_env_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_ENGINE_MODE", "balanced")
        monkeypatch.setenv("DEBATE_ENGINE_PROVIDER", "anthropic")
        monkeypatch.setenv("DEBATE_ENGINE_MODEL", "claude-sonnet-4-20250514")
        monkeypatch.setenv("DEBATE_ENGINE_BACKUP_PROVIDER", "openai")
        monkeypatch.setenv("DEBATE_ENGINE_BACKUP_MODEL", "gpt-4o")
        monkeypatch.setenv("DEBATE_ENGINE_JUDGE_MODEL", "gpt-4o")
        monkeypatch.setenv("DEBATE_ENGINE_TIMEOUT", "60")
        monkeypatch.setenv("DEBATE_ENGINE_MAX_TRANSPORT_RETRIES", "5")
        monkeypatch.setenv("DEBATE_ENGINE_MAX_PARSE_RETRIES", "3")

        config = ProviderConfig.from_env()
        assert config.mode == ProviderMode.BALANCED
        assert config.primary_provider == "anthropic"
        assert config.primary_model == "claude-sonnet-4-20250514"
        assert config.backup_provider == "openai"
        assert config.backup_model == "gpt-4o"
        assert config.judge_model == "gpt-4o"
        assert config.timeout_seconds == 60.0
        assert config.max_transport_retries == 5
        assert config.max_parse_retries == 3

    def test_from_env_invalid_mode_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_ENGINE_MODE", "invalid_mode")
        config = ProviderConfig.from_env()
        assert config.mode == ProviderMode.STABLE

    def test_from_env_api_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")

        config = ProviderConfig.from_env()
        assert config.primary_api_key == "sk-test-openai"
        assert config.backup_api_key == "sk-test-anthropic"


# ===================================================================
# Model selection tests
# ===================================================================


class TestModelSelection:
    """Test _get_model_for_role for different provider modes."""

    def test_stable_mode_default_roles(self) -> None:
        provider = LLMProvider(ProviderConfig(mode=ProviderMode.STABLE))

        prov, model = provider._get_model_for_role("critic_a")
        assert prov == "openai"
        assert model == "gpt-4o-mini"

        prov, model = provider._get_model_for_role("critic_b")
        assert prov == "openai"
        assert model == "gpt-4o-mini"

    def test_stable_mode_judge(self) -> None:
        provider = LLMProvider(
            ProviderConfig(
                mode=ProviderMode.STABLE,
                judge_model="gpt-4o",
            ),
        )
        prov, model = provider._get_model_for_role("judge")
        assert prov == "openai"
        assert model == "gpt-4o"

    def test_balanced_mode_devil_advocate_uses_backup(self) -> None:
        provider = LLMProvider(
            ProviderConfig(
                mode=ProviderMode.BALANCED,
                backup_provider="anthropic",
                backup_model="claude-sonnet-4-20250514",
            ),
        )
        prov, model = provider._get_model_for_role("devil_advocate")
        assert prov == "anthropic"
        assert model == "claude-sonnet-4-20250514"

    def test_balanced_mode_devil_advocate_no_backup_falls_to_primary(self) -> None:
        provider = LLMProvider(ProviderConfig(mode=ProviderMode.BALANCED))
        prov, model = provider._get_model_for_role("devil_advocate")
        # Falls back to primary when backup not configured
        assert prov == "openai"
        assert model == "gpt-4o-mini"

    def test_balanced_mode_judge_uses_backup(self) -> None:
        provider = LLMProvider(
            ProviderConfig(
                mode=ProviderMode.BALANCED,
                backup_provider="anthropic",
                backup_model="claude-sonnet-4-20250514",
            ),
        )
        prov, model = provider._get_model_for_role("judge")
        # In BALANCED mode, judge uses backup provider but primary model
        # (effective_judge_model defaults to primary_model unless judge_model is set)
        assert prov == "anthropic"
        assert model == "gpt-4o-mini"  # primary_model since judge_model not set

    def test_balanced_mode_non_da_roles_use_primary(self) -> None:
        provider = LLMProvider(
            ProviderConfig(
                mode=ProviderMode.BALANCED,
                backup_provider="anthropic",
                backup_model="claude-sonnet-4-20250514",
            ),
        )
        prov, model = provider._get_model_for_role("critic_a")
        assert prov == "openai"
        assert model == "gpt-4o-mini"


# ===================================================================
# JSON parsing tests
# ===================================================================


class TestJSONParsing:
    """Test _parse_json_response with various input formats."""

    def test_valid_json(self) -> None:
        text = '{"target_area": "test", "defect_type": "GENERAL", "severity": "MINOR", "evidence": "This is valid evidence for testing.", "suggested_fix": "This is a valid suggested fix.", "fix_kind": "CONCRETE_FIX", "confidence": 0.8}'
        result = LLMProvider._parse_json_response(text, None)
        assert result == text  # No response_model -> returns raw text

    def test_json_in_markdown_code_block(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        result = LLMProvider._parse_json_response(text, None)
        # Should strip code fences and return inner text
        assert "key" in result

    def test_none_raw_response_raises(self) -> None:
        with pytest.raises(ValueError, match="Raw response is None"):
            LLMProvider._parse_json_response(None, None)


# ===================================================================
# Transport / retry logic tests
# ===================================================================


class TestTransportRetry:
    """Test retry logic with mocked litellm calls."""

    def _make_messages(self) -> list[dict[str, str]]:
        return [{"role": "user", "content": "Evaluate this content."}]

    @pytest.mark.asyncio
    async def test_retry_on_429_then_success(self) -> None:
        """Test that a 429 error triggers retry and subsequent success."""
        config = ProviderConfig(
            max_transport_retries=3,
            timeout_seconds=10.0,
        )
        provider = LLMProvider(config)
        messages = self._make_messages()

        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success response"

        call_count = 0

        async def mock_acompletion(params: Any, response_model: Any = None) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Rate limit exceeded")
            return ("Success response", mock_response)

        with patch.object(provider, "_acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = mock_acompletion

            result, call_result = await provider.call(
                messages=messages,
                role_type="critic_a",
            )

        # Should have retried (2+ calls)
        assert call_count >= 2
        assert call_result.status == "SUCCESS"

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self) -> None:
        """Test that non-retryable errors do not trigger retries."""
        config = ProviderConfig(
            max_transport_retries=3,
            timeout_seconds=10.0,
        )
        provider = LLMProvider(config)
        messages = self._make_messages()

        call_count = 0

        async def mock_acompletion(params: Any, response_model: Any = None) -> Any:
            nonlocal call_count
            call_count += 1
            raise ValueError("Authentication failed: invalid API key")

        with patch.object(provider, "_acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = mock_acompletion

            result, call_result = await provider.call(
                messages=messages,
                role_type="critic_a",
            )

        assert call_result.status == "ROLE_FAILED"
        # Should only be called once (no retries for auth errors)
        assert call_count == 1


# ===================================================================
# Cost tracking tests
# ===================================================================


class TestCostTracking:
    """Test cost accumulation."""

    def test_initial_cost_is_zero(self) -> None:
        provider = LLMProvider(ProviderConfig())
        assert provider.cost_accumulated == 0.0
        assert provider.call_count == 0

    @pytest.mark.asyncio
    async def test_cost_accumulation(self) -> None:
        config = ProviderConfig(timeout_seconds=10.0)
        provider = LLMProvider(config)
        messages = [{"role": "user", "content": "test"}]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"

        async def mock_acompletion(params: Any, response_model: Any = None) -> Any:
            return ("response", mock_response)

        with patch.object(provider, "_acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = mock_acompletion
            with patch.object(provider, "_track_cost", return_value=0.005) as mock_cost:
                await provider.call(messages=messages, role_type="critic_a")
                await provider.call(messages=messages, role_type="critic_b")
                assert mock_cost.call_count == 2


# ===================================================================
# Timeout tests
# ===================================================================


class TestTimeoutHandling:
    """Test timeout handling for LLM calls."""

    @pytest.mark.asyncio
    async def test_timeout_returns_role_failed(self) -> None:
        config = ProviderConfig(timeout_seconds=0.01, max_transport_retries=0)
        provider = LLMProvider(config)
        messages = [{"role": "user", "content": "test"}]

        async def slow_call(params: Any, response_model: Any = None) -> Any:
            await asyncio.sleep(10)  # Much longer than 0.01s timeout
            return MagicMock()

        with patch.object(provider, "_acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = slow_call

            result, call_result = await provider.call(
                messages=messages,
                role_type="critic_a",
            )

        assert call_result.status == "ROLE_FAILED"
        assert "timed out" in (call_result.error_message or "").lower()


# ===================================================================
# Error classification tests
# ===================================================================


class TestErrorClassification:
    """Test _is_retryable error classification."""

    def test_429_is_retryable(self) -> None:
        assert LLMProvider._is_retryable(Exception("429 Rate limit exceeded")) is True

    def test_500_is_retryable(self) -> None:
        assert LLMProvider._is_retryable(Exception("500 Internal Server Error")) is True

    def test_503_is_retryable(self) -> None:
        assert LLMProvider._is_retryable(Exception("503 Service Unavailable")) is True

    def test_connection_error_is_retryable(self) -> None:
        assert LLMProvider._is_retryable(ConnectionError("Connection refused")) is True

    def test_timeout_error_is_retryable(self) -> None:
        assert LLMProvider._is_retryable(TimeoutError("Request timed out")) is True

    def test_auth_error_is_not_retryable(self) -> None:
        assert LLMProvider._is_retryable(ValueError("Authentication failed")) is False

    def test_generic_error_is_not_retryable(self) -> None:
        assert LLMProvider._is_retryable(RuntimeError("Something unexpected")) is False


# ===================================================================
# ProviderEntry and failover chain tests
# ===================================================================


class TestProviderEntry:
    """Test ProviderEntry dataclass."""

    def test_creation(self) -> None:
        entry = ProviderEntry(
            name="Google AI Studio",
            model="gemini-2.5-flash",
            api_key="test-key",
            api_base=None,
            priority=1,
        )
        assert entry.name == "Google AI Studio"
        assert entry.model == "gemini-2.5-flash"
        assert entry.api_key == "test-key"
        assert entry.priority == 1

    def test_defaults(self) -> None:
        entry = ProviderEntry()
        assert entry.name == ""
        assert entry.model == ""
        assert entry.api_key is None
        assert entry.api_base is None
        assert entry.priority == 1


class TestFailoverChain:
    """Test failover chain resolution and provider selection."""

    def test_resolved_chain_from_providers_field(self) -> None:
        """When providers field is set, it takes precedence."""
        config = ProviderConfig(
            providers=[
                ProviderEntry(name="groq", model="llama-3.3-70b", priority=2),
                ProviderEntry(name="google", model="gemini-2.5-flash", priority=1),
            ],
        )
        chain = config._resolved_chain
        assert len(chain) == 2
        assert chain[0].name == "google"  # priority 1 first
        assert chain[1].name == "groq"    # priority 2 second

    def test_resolved_chain_backward_compat(self) -> None:
        """When providers is empty, chain is synthesised from primary/backup."""
        config = ProviderConfig(
            primary_provider="openai",
            primary_model="gpt-4o-mini",
            backup_provider="anthropic",
            backup_model="claude-sonnet-4-20250514",
        )
        chain = config._resolved_chain
        assert len(chain) == 2
        assert chain[0].name == "openai"
        assert chain[0].model == "gpt-4o-mini"
        assert chain[1].name == "anthropic"
        assert chain[1].model == "claude-sonnet-4-20250514"

    def test_resolved_chain_no_backup(self) -> None:
        """When no backup, chain has only primary."""
        config = ProviderConfig(
            primary_provider="openai",
            primary_model="gpt-4o-mini",
        )
        chain = config._resolved_chain
        assert len(chain) == 1
        assert chain[0].name == "openai"

    def test_get_failover_chain_for_role(self) -> None:
        """Test _get_failover_chain returns correct chain for a role."""
        config = ProviderConfig(
            providers=[
                ProviderEntry(name="google", model="gemini-2.5-flash", priority=1),
                ProviderEntry(name="groq", model="llama-3.3-70b", priority=2),
            ],
        )
        provider = LLMProvider(config)
        chain = provider._get_failover_chain("critic_a")
        assert len(chain) == 2
        assert chain[0][0] == "google"
        assert chain[0][1] == "gemini-2.5-flash"
        assert chain[1][0] == "groq"
        assert chain[1][1] == "llama-3.3-70b"

    def test_from_env_with_failover_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that failover chain is built when failover env keys are present."""
        monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
        monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
        monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-key")

        config = ProviderConfig.from_env()
        assert len(config.providers) == 3
        assert config.providers[0].name == "Google AI Studio"
        assert config.providers[0].api_key == "google-test-key"
        assert config.providers[1].name == "Groq"
        assert config.providers[1].api_key == "groq-test-key"
        assert config.providers[2].name == "NVIDIA NIM"
        assert config.providers[2].api_key == "nvidia-test-key"

    def test_from_env_partial_failover_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that only configured providers appear in chain."""
        monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
        # No GROQ or NVIDIA keys

        config = ProviderConfig.from_env()
        assert len(config.providers) == 1
        assert config.providers[0].name == "Google AI Studio"

    def test_from_env_no_failover_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test backward compat when no failover keys are present."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

        config = ProviderConfig.from_env()
        assert config.providers == []
        # Should still work with primary/backup fields
        assert config.primary_provider == "openai"
        assert config.primary_model == "gpt-4o-mini"

    def test_model_selection_uses_failover_chain(self) -> None:
        """Test that _get_model_for_role uses the failover chain."""
        config = ProviderConfig(
            providers=[
                ProviderEntry(name="google", model="gemini-2.5-flash", priority=1),
            ],
        )
        provider = LLMProvider(config)
        prov, model = provider._get_model_for_role("critic_a")
        assert prov == "google"
        assert model == "gemini-2.5-flash"
