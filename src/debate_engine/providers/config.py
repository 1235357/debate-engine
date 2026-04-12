"""Provider configuration with multi-mode support (STABLE / BALANCED / DIVERSE)."""

from __future__ import annotations
import enum
import os
from dataclasses import dataclass


class ProviderMode(str, enum.Enum):
    STABLE = "stable"
    BALANCED = "balanced"
    DIVERSE = "diverse"


@dataclass
class ProviderConfig:
    mode: ProviderMode = ProviderMode.STABLE
    primary_provider: str = "openai"
    primary_model: str = "gpt-4o-mini"
    primary_api_key: str | None = None
    primary_api_base: str | None = None
    backup_provider: str | None = None
    backup_model: str | None = None
    backup_api_key: str | None = None
    backup_api_base: str | None = None
    judge_model: str | None = None
    timeout_seconds: float = 25.0
    max_transport_retries: int = 2
    max_parse_retries: int = 1

    @property
    def effective_judge_model(self) -> str:
        return self.judge_model or self.primary_model

    @property
    def effective_judge_provider(self) -> str:
        if self.mode == ProviderMode.BALANCED and self.backup_provider:
            return self.backup_provider
        return self.primary_provider

    @classmethod
    def from_env(cls) -> ProviderConfig:
        mode_str = os.getenv("DEBATE_ENGINE_MODE", "stable")
        try:
            mode = ProviderMode(mode_str)
        except ValueError:
            mode = ProviderMode.STABLE
        primary_provider = os.getenv("DEBATE_ENGINE_PROVIDER", "openai")
        primary_model = os.getenv("DEBATE_ENGINE_MODEL", "gpt-4o-mini")
        primary_api_key = os.getenv("OPENAI_API_KEY")
        primary_api_base = os.getenv("OPENAI_API_BASE")
        backup_provider = os.getenv("DEBATE_ENGINE_BACKUP_PROVIDER")
        backup_model = os.getenv("DEBATE_ENGINE_BACKUP_MODEL")
        backup_api_key = os.getenv("ANTHROPIC_API_KEY")
        backup_api_base = os.getenv("ANTHROPIC_API_BASE")
        judge_model = os.getenv("DEBATE_ENGINE_JUDGE_MODEL")
        timeout = float(os.getenv("DEBATE_ENGINE_TIMEOUT", "25.0"))
        max_transport = int(os.getenv("DEBATE_ENGINE_MAX_TRANSPORT_RETRIES", "2"))
        max_parse = int(os.getenv("DEBATE_ENGINE_MAX_PARSE_RETRIES", "1"))
        return cls(
            mode=mode, primary_provider=primary_provider, primary_model=primary_model,
            primary_api_key=primary_api_key, primary_api_base=primary_api_base,
            backup_provider=backup_provider, backup_model=backup_model,
            backup_api_key=backup_api_key, backup_api_base=backup_api_base,
            judge_model=judge_model, timeout_seconds=timeout,
            max_transport_retries=max_transport, max_parse_retries=max_parse,
        )