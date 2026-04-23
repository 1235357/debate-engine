"""Provider configuration with multi-mode support and multi-source failover chain."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum


class ProviderMode(StrEnum):
    STABLE = "stable"
    BALANCED = "balanced"
    DIVERSE = "diverse"


@dataclass
class ProviderEntry:
    name: str = ""
    model: str = ""
    api_key: str | None = None
    api_base: str | None = None
    priority: int = 1


_DEFAULT_FAILOVER_CHAIN: list[ProviderEntry] = [
    ProviderEntry(name="Google AI Studio", model="gemini-2.5-flash", priority=1),
    ProviderEntry(name="Groq", model="llama-3.3-70b-versatile", priority=2),
    ProviderEntry(name="NVIDIA NIM", model="minimax-m2.7", priority=3),
]


@dataclass
class ProviderConfig:
    mode: ProviderMode = ProviderMode.STABLE
    providers: list[ProviderEntry] = field(default_factory=list)
    primary_provider: str = "nvidia"
    primary_model: str = "minimax-m2.7"
    primary_api_key: str | None = None
    primary_api_base: str | None = "https://integrate.api.nvidia.com/v1"
    backup_provider: str | None = None
    backup_model: str | None = None
    backup_api_key: str | None = None
    backup_api_base: str | None = None
    judge_model: str | None = None
    timeout_seconds: float = 120.0
    max_transport_retries: int = 2
    max_parse_retries: int = 1

    @property
    def effective_judge_model(self) -> str:
        if self.judge_model:
            return self.judge_model
        chain = self._resolved_chain
        return chain[0].model if chain else self.primary_model

    @property
    def effective_judge_provider(self) -> str:
        if self.mode == ProviderMode.BALANCED and self.backup_provider:
            return self.backup_provider
        chain = self._resolved_chain
        return chain[0].name.lower().replace(" ", "_") if chain else self.primary_provider

    @property
    def _resolved_chain(self) -> list[ProviderEntry]:
        if self.providers:
            return sorted(self.providers, key=lambda p: p.priority)
        chain = [
            ProviderEntry(
                name=self.primary_provider,
                model=self.primary_model,
                api_key=self.primary_api_key,
                api_base=self.primary_api_base,
                priority=1,
            )
        ]
        if self.backup_provider and self.backup_model:
            chain.append(
                ProviderEntry(
                    name=self.backup_provider,
                    model=self.backup_model,
                    api_key=self.backup_api_key,
                    api_base=self.backup_api_base,
                    priority=2,
                )
            )
        return chain

    @classmethod
    def from_env(cls) -> ProviderConfig:
        # 同时支持 DEBATE_ENGINE_PROVIDER_MODE 和 DEBATE_ENGINE_MODE
        mode_str = os.getenv(
            "DEBATE_ENGINE_PROVIDER_MODE", os.getenv("DEBATE_ENGINE_MODE", "stable")
        )
        # 确保模式字符串为小写，与枚举值一致
        mode_str = mode_str.lower()
        try:
            mode = ProviderMode(mode_str)
        except ValueError:
            mode = ProviderMode.STABLE
        primary_provider = os.getenv("DEBATE_ENGINE_PROVIDER", "nvidia")
        primary_model = os.getenv("DEBATE_ENGINE_MODEL", "minimax-m2.7")
        primary_api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
        primary_api_base = os.getenv(
            "NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"
        ) or os.getenv("OPENAI_API_BASE")
        backup_provider = os.getenv("DEBATE_ENGINE_BACKUP_PROVIDER")
        backup_model = os.getenv("DEBATE_ENGINE_BACKUP_MODEL")
        backup_api_key = os.getenv("ANTHROPIC_API_KEY")
        backup_api_base = os.getenv("ANTHROPIC_API_BASE")
        judge_model = os.getenv("DEBATE_ENGINE_JUDGE_MODEL")
        timeout = float(os.getenv("DEBATE_ENGINE_TIMEOUT", "120.0"))
        max_transport = int(os.getenv("DEBATE_ENGINE_MAX_TRANSPORT_RETRIES", "2"))
        max_parse = int(os.getenv("DEBATE_ENGINE_MAX_PARSE_RETRIES", "1"))
        google_key = os.getenv("GOOGLE_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        providers = []
        if nvidia_key:
            providers.append(
                ProviderEntry(
                    name="NVIDIA NIM",
                    model="minimax-m2.7",
                    api_key=nvidia_key,
                    api_base="https://integrate.api.nvidia.com/v1",
                    priority=1,
                )
            )
        if google_key:
            providers.append(
                ProviderEntry(
                    name="Google AI Studio",
                    model="gemini-2.5-flash",
                    api_key=google_key,
                    priority=2,
                )
            )
        if groq_key:
            providers.append(
                ProviderEntry(
                    name="Groq", model="llama-3.3-70b-versatile", api_key=groq_key, priority=3
                )
            )
        return cls(
            mode=mode,
            providers=providers,
            primary_provider=primary_provider,
            primary_model=primary_model,
            primary_api_key=primary_api_key,
            primary_api_base=primary_api_base,
            backup_provider=backup_provider,
            backup_model=backup_model,
            backup_api_key=backup_api_key,
            backup_api_base=backup_api_base,
            judge_model=judge_model,
            timeout_seconds=timeout,
            max_transport_retries=max_transport,
            max_parse_retries=max_parse,
        )
