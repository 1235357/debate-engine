"""LLM Provider wrapping LiteLLM with retry logic, structured output, and cost tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from ..api.key_manager import APIKeyManager
from .config import ProviderConfig, ProviderMode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CallResult:
    """Result metadata for a single LLM call.

    Attributes:
        status: Outcome of the call (SUCCESS / PARSE_FAILED / ROLE_FAILED).
        cost_usd: Estimated cost in USD via ``litellm.completion_cost``.
        latency_ms: Wall-clock latency of the call in milliseconds.
        model_used: The model identifier that was actually called.
        parse_attempts: Number of parse attempts (1 = first try, 2 = one repair).
        raw_response: The raw text returned by the LLM, if available.
        error_message: Human-readable error description when the call failed.
    """

    status: Literal["SUCCESS", "PARSE_FAILED", "ROLE_FAILED"] = "SUCCESS"
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    model_used: str = ""
    parse_attempts: int = 1
    raw_response: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# LLMProvider
# ---------------------------------------------------------------------------


class LLMProvider:
    """Wraps LiteLLM with retry logic, structured output, and cost tracking.

    Features
    --------
    * **Transport retry** -- exponential backoff (1 s, 2 s) for network / 429 /
      5xx errors, up to ``config.max_transport_retries`` attempts.
    * **Parse repair** -- on Pydantic validation failure the error message is
      fed back to the LLM for one more attempt (up to
      ``config.max_parse_retries`` repairs).
    * **Cost tracking** -- cumulative USD cost via ``litellm.completion_cost``.
    * **Timeout control** -- per-call ``asyncio.wait_for`` using
      ``config.timeout_seconds``.
    * **Structured output** -- uses Instructor patching when available, falls
      back to JSON-mode + manual Pydantic parsing otherwise.
    * **API Key Load Balancing** -- distributes requests across multiple API keys
      with failover and success/failure tracking.
    """

    def __init__(self, config: ProviderConfig, key_manager: APIKeyManager | None = None) -> None:
        self.config = config
        self.key_manager = key_manager
        self._cost_accumulated: float = 0.0
        self._call_count: int = 0
        self._instructor_available: bool | None = None  # lazy-detect

    # -- public properties ----------------------------------------------------

    @property
    def cost_accumulated(self) -> float:
        """Cumulative cost in USD across all calls made by this provider."""
        return self._cost_accumulated

    @property
    def call_count(self) -> int:
        """Total number of LLM calls (including retries) made."""
        return self._call_count

    # -- public API -----------------------------------------------------------

    async def call(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        response_model: type[BaseModel] | None = None,
        role_type: str = "critic",
        temperature: float = 0.3,
    ) -> tuple[Any, CallResult]:
        """Make an LLM call with retry, parse repair, and cost tracking.

        Parameters
        ----------
        messages:
            Conversation messages (OpenAI-compatible format).
        system_prompt:
            Optional system prompt prepended to the message list.
        response_model:
            Pydantic model for structured output.  When provided the response
            is parsed into this model; otherwise the raw text is returned.
        role_type:
            Semantic role hint (``"critic_a"``, ``"critic_b"``,
            ``"devil_advocate"``, ``"judge"``).  Used by
            :meth:`_get_model_for_role` to select the provider/model pair.
        temperature:
            Sampling temperature.

        Returns
        -------
        tuple[Any, CallResult]
            A ``(parsed_result, call_result)`` pair.  *parsed_result* is an
            instance of *response_model* when provided, otherwise the raw
            response string.  *call_result* carries metadata about the call.
        """
        provider, model = self._get_model_for_role(role_type)
        model_display = f"{provider}/{model}"

        start = time.monotonic()
        raw_response: str | None = None
        parse_attempts = 0
        status: Literal["SUCCESS", "PARSE_FAILED", "ROLE_FAILED"] = "ROLE_FAILED"
        error_message: str | None = None
        parsed: Any = None
        cost_usd = 0.0

        # -- Get failover chain for automatic provider failover -----------------
        failover_chain = self._get_failover_chain(role_type)

        # -- Build litellm params ---------------------------------------------
        litellm_params = self._build_litellm_params(
            provider=provider,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        # -- Transport retry loop with failover --------------------------------
        last_transport_error: Exception | None = None
        chain_index = 0  # Track which provider in the chain we're using
        for transport_attempt in range(1, self.config.max_transport_retries + 2):
            backoff = 2 ** (transport_attempt - 1)  # 1, 2, 4 …
            if transport_attempt > 1:
                logger.warning(
                    "Transport retry %d/%d for %s (backoff %ds)",
                    transport_attempt - 1,
                    self.config.max_transport_retries,
                    model_display,
                    backoff,
                )
                await asyncio.sleep(backoff)

            try:
                response = await asyncio.wait_for(
                    self._acompletion(litellm_params, response_model),
                    timeout=self.config.timeout_seconds,
                )
                self._call_count += 1

                # response is either (raw_text, response_obj) or a parsed model
                if isinstance(response, tuple):
                    raw_response, response_obj = response
                else:
                    # Instructor returned a parsed model directly
                    parsed = response
                    raw_response = response.model_dump_json()
                    response_obj = None

                # Track cost
                cost_usd = self._track_cost(response_obj)

                # If Instructor handled parsing, we are done
                if parsed is not None:
                    status = "SUCCESS"
                    parse_attempts = 1
                    break

                # -- Parse repair loop -----------------------------------------
                for parse_attempt in range(1, self.config.max_parse_retries + 2):
                    parse_attempts = parse_attempt
                    try:
                        parsed = self._parse_json_response(raw_response, response_model)
                        status = "SUCCESS"
                        break
                    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                        logger.warning(
                            "Parse attempt %d/%d failed for %s: %s",
                            parse_attempt,
                            self.config.max_parse_retries + 1,
                            model_display,
                            exc,
                        )
                        if parse_attempt <= self.config.max_parse_retries:
                            # Feed error back for repair
                            repair_messages = list(messages)
                            repair_messages.append(
                                {
                                    "role": "user",
                                    "content": (
                                        "Your previous response could not be parsed. "
                                        f"Error: {exc}\n\n"
                                        "Please fix your response and output valid JSON "
                                        "matching the required schema."
                                    ),
                                }
                            )
                            litellm_params["messages"] = (
                                (
                                    [{"role": "system", "content": system_prompt}]
                                    if system_prompt
                                    else []
                                )
                                + repair_messages
                                if system_prompt
                                else repair_messages
                                if not system_prompt
                                else (
                                    [{"role": "system", "content": system_prompt}] + repair_messages
                                )
                            )
                            try:
                                repair_resp = await asyncio.wait_for(
                                    self._acompletion(litellm_params, None),
                                    timeout=self.config.timeout_seconds,
                                )
                                self._call_count += 1
                                if isinstance(repair_resp, tuple):
                                    raw_response, response_obj = repair_resp
                                    cost_usd += self._track_cost(response_obj)
                                else:
                                    raw_response = str(repair_resp)
                            except Exception as repair_exc:
                                logger.error("Parse repair LLM call failed: %s", repair_exc)
                                break
                        else:
                            error_message = str(exc)
                # end parse repair loop

                # If parse repair didn't succeed, set status
                if status != "SUCCESS":
                    status = "PARSE_FAILED"
                    error_message = error_message or "All parse attempts exhausted"
                break  # transport succeeded, exit transport retry loop

            except TimeoutError:
                last_transport_error = TimeoutError(
                    f"Call to {model_display} timed out after {self.config.timeout_seconds}s"
                )
                error_message = str(last_transport_error)
                logger.warning("Timeout for %s (attempt %d)", model_display, transport_attempt)
            except Exception as exc:
                last_transport_error = exc
                error_message = str(exc)
                # Classify: retry on network / 429 / 5xx
                if self._is_retryable(exc):
                    logger.warning(
                        "Retryable error for %s (attempt %d): %s",
                        model_display,
                        transport_attempt,
                        exc,
                    )
                    # Attempt failover to next provider in chain
                    chain_index += 1
                    if chain_index < len(failover_chain):
                        next_provider, next_model, next_api_key, next_api_base = failover_chain[
                            chain_index
                        ]
                        provider = next_provider
                        model = next_model
                        model_display = f"{provider}/{model}"
                        litellm_params = self._build_litellm_params(
                            provider=provider,
                            model=model,
                            messages=messages,
                            system_prompt=system_prompt,
                            temperature=temperature,
                        )
                        # Inject API key/base if available
                        if next_api_key:
                            litellm_params["api_key"] = next_api_key
                        if next_api_base:
                            litellm_params["api_base"] = next_api_base
                        logger.info(
                            "Failing over to provider %s (chain index %d)",
                            model_display,
                            chain_index,
                        )
                else:
                    logger.error("Non-retryable error for %s: %s", model_display, exc)
                    break  # don't retry non-retryable errors
        # end transport retry loop

        if status == "ROLE_FAILED" and last_transport_error:
            error_message = error_message or str(last_transport_error)

        latency_ms = (time.monotonic() - start) * 1000

        call_result = CallResult(
            status=status,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            model_used=model_display,
            parse_attempts=parse_attempts,
            raw_response=raw_response,
            error_message=error_message,
        )

        logger.info(
            "LLM call complete: status=%s model=%s cost=%.6f latency=%.0fms parse_attempts=%d",
            status,
            model_display,
            cost_usd,
            latency_ms,
            parse_attempts,
        )

        return parsed if parsed is not None else raw_response, call_result

    # -- Role-based model selection -------------------------------------------

    def _map_provider_name(self, provider_name: str) -> str:
        """Map provider names to LiteLLM official routes.

        Args:
            provider_name: The provider name to map

        Returns:
            The mapped provider name that matches LiteLLM official routes
        """
        mapped_name = provider_name.lower().replace(" ", "_")
        if mapped_name == "google_ai_studio":
            return "gemini"
        elif mapped_name == "nvidia_nim":
            return "nvidia"
        return mapped_name

    def _get_model_for_role(self, role_type: str) -> tuple[str, str]:
        """Return ``(provider, model)`` based on provider mode and role type.

        Uses the failover chain when available.  The first entry in the chain
        is the preferred provider; subsequent entries are used as fallbacks
        on 429/5xx errors.

        STABLE mode
        -----------
        All roles use the first provider in the failover chain (or the
        primary provider/model for backward compatibility).  The Judge role
        uses ``effective_judge_model`` / ``effective_judge_provider``.

        BALANCED mode
        -------------
        * ``devil_advocate`` uses the backup provider/model (if configured),
          falling back to primary when backup is unavailable.
        * ``judge`` uses the backup provider with ``effective_judge_model``
          (or primary if backup is not set).
        * All other roles use the primary provider/model.
        """
        cfg = self.config

        # Judge role -- always use the judge-specific provider/model
        if role_type == "judge":
            return self._map_provider_name(cfg.effective_judge_provider), cfg.effective_judge_model

        # BALANCED mode: DA role uses backup provider
        if cfg.mode == ProviderMode.BALANCED and role_type == "devil_advocate":
            if cfg.backup_provider and cfg.backup_model:
                return self._map_provider_name(cfg.backup_provider), cfg.backup_model
            # Fallback to primary if backup is not configured
            logger.warning(
                "BALANCED mode requested but backup provider not configured; "
                "falling back to primary for devil_advocate role"
            )
            return self._map_provider_name(cfg.primary_provider), cfg.primary_model

        # Use failover chain if available
        chain = cfg._resolved_chain
        if chain:
            entry = chain[0]
            return self._map_provider_name(entry.name), entry.model

        # Default: primary provider/model
        return self._map_provider_name(cfg.primary_provider), cfg.primary_model

    def _get_failover_chain(self, role_type: str) -> list[tuple[str, str, str | None, str | None]]:
        """Return the full failover chain for a given role type.

        Each entry is ``(provider, model, api_key, api_base)``.  The first
        entry is the preferred provider; subsequent entries are fallbacks.
        """
        cfg = self.config

        # Judge role uses its own provider/model
        if role_type == "judge":
            chain = cfg._resolved_chain
            if chain:
                return [
                    (self._map_provider_name(e.name), e.model, e.api_key, e.api_base) for e in chain
                ]
            return [
                (
                    self._map_provider_name(cfg.effective_judge_provider),
                    cfg.effective_judge_model,
                    cfg.primary_api_key,
                    cfg.primary_api_base,
                )
            ]

        # BALANCED mode: DA role uses backup first, then primary
        if cfg.mode == ProviderMode.BALANCED and role_type == "devil_advocate":
            if cfg.backup_provider and cfg.backup_model:
                return [
                    (
                        cfg.backup_provider,
                        cfg.backup_model,
                        cfg.backup_api_key,
                        cfg.backup_api_base,
                    ),
                    (
                        cfg.primary_provider,
                        cfg.primary_model,
                        cfg.primary_api_key,
                        cfg.primary_api_base,
                    ),
                ]

        # Use full failover chain
        chain = cfg._resolved_chain
        if chain:
            return [
                (self._map_provider_name(e.name), e.model, e.api_key, e.api_base) for e in chain
            ]

        # Backward compat: primary only
        return [
            (
                self._map_provider_name(cfg.primary_provider),
                cfg.primary_model,
                cfg.primary_api_key,
                cfg.primary_api_base,
            )
        ]

    # -- LiteLLM completion ---------------------------------------------------

    def _build_litellm_params(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: str | None,
        temperature: float,
    ) -> dict[str, Any]:
        """Build kwargs for LLM completion."""
        full_messages: list[dict] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # 构建基础参数
        params: dict[str, Any] = {
            "messages": full_messages,
            "temperature": temperature,
        }

        if provider == "nvidia":
            # NVIDIA API - 直接使用模型名称和API地址
            params["model"] = model
            if self.config.primary_api_base:
                params["api_base"] = self.config.primary_api_base
            else:
                params["api_base"] = "https://integrate.api.nvidia.com/v1"
        else:
            # 其他提供商的处理
            if "/" not in model:
                params["model"] = f"{provider}/{model}"
            else:
                params["model"] = model

        # Add API key from key manager if available
        if self.key_manager:
            api_key = self.key_manager.get_next_key()
            params["api_key"] = api_key
        elif self.config.primary_api_key:
            params["api_key"] = self.config.primary_api_key

        return params

    async def _acompletion(
        self,
        params: dict[str, Any],
        response_model: type[BaseModel] | None,
    ) -> Any:
        """Call LLM, using direct OpenAI client for NVIDIA API or LiteLLM otherwise.

        Returns either a ``(raw_text, response_obj)`` tuple or, when
        Instructor is used, the parsed Pydantic model directly.
        """
        api_key = params.get("api_key")
        
        # 检查是否是NVIDIA API调用
        model = params.get("model", "")
        is_nvidia = model.startswith("minimaxai/") or params.get("api_base", "").find("nvidia.com") != -1

        try:
            if is_nvidia:
                # NVIDIA API - 直接使用OpenAI客户端，按照官方文档方式
                from openai import AsyncOpenAI
                
                # 提取参数
                api_base = params.get("api_base", "https://integrate.api.nvidia.com/v1")
                messages = params.get("messages", [])
                temperature = params.get("temperature", 0.7)
                
                # 创建客户端
                client = AsyncOpenAI(
                    base_url=api_base,
                    api_key=api_key
                )
                
                if response_model is not None:
                    # 对于需要结构化输出的，我们先获取原始文本，然后手动解析
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=4096,
                        stream=False
                    )
                    raw_text = response.choices[0].message.content or ""
                    result = raw_text, response
                else:
                    # 标准调用
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=4096,
                        stream=False
                    )
                    raw_text = response.choices[0].message.content or ""
                    result = raw_text, response
            else:
                import litellm  # late import to avoid hard dependency at module level
                
                # 其他提供商使用LiteLLM
                if response_model is not None and self._check_instructor():
                    result = await self._acompletion_with_instructor(params, response_model)
                else:
                    # Standard litellm.acompletion
                    response = await litellm.acompletion(**params)
                    raw_text = response.choices[0].message.content or ""
                    result = raw_text, response

            # Record success if API key was used
            if self.key_manager and api_key:
                self.key_manager.record_success(api_key)

            return result
        except Exception:
            # Record failure if API key was used
            if self.key_manager and api_key:
                self.key_manager.record_failure(api_key)
            raise

    def _check_instructor(self) -> bool:
        """Lazily detect whether Instructor is available."""
        if self._instructor_available is None:
            try:
                import instructor  # noqa: F401

                self._instructor_available = True
            except ImportError:
                self._instructor_available = False
                logger.debug("Instructor not available; falling back to JSON mode")
        return self._instructor_available

    async def _acompletion_with_instructor(
        self,
        params: dict[str, Any],
        response_model: type[BaseModel],
    ) -> Any:
        """Use Instructor for structured output extraction, or fallback to manual parsing for NVIDIA."""
        # 检查是否是NVIDIA API
        model = params.get("model", "")
        is_nvidia = model.startswith("minimaxai/") or params.get("api_base", "").find("nvidia.com") != -1
        
        if is_nvidia:
            # NVIDIA API不使用Instructor，回退到手动解析
            # 先调用标准API获取原始文本
            result = await self._acompletion(params, None)
            raw_text, response_obj = result
            # 手动解析JSON
            parsed = self._parse_json_response(raw_text, response_model)
            return parsed
        else:
            # 其他提供商使用Instructor
            import instructor
            import litellm

            api_key = params.get("api_key")

            client = instructor.from_litellm(litellm.AsyncOpenAI())
            # Extract model string from params
            model = params.pop("model")
            messages = params.pop("messages")
            temperature = params.pop("temperature", 0.3)

            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_model=response_model,
                    **params,
                )
                # Record success if API key was used
                if self.key_manager and api_key:
                    self.key_manager.record_success(api_key)
                return response
            except Exception:
                # Record failure if API key was used
                if self.key_manager and api_key:
                    self.key_manager.record_failure(api_key)
                raise

    # -- Parsing helpers ------------------------------------------------------

    @staticmethod
    def _parse_json_response(raw: str | None, response_model: type[BaseModel] | None) -> Any:
        """Parse raw LLM text into a Pydantic model.

        Attempts to extract JSON from the raw text (handles markdown code
        fences) and validates against *response_model*.
        """
        if raw is None:
            raise ValueError("Raw response is None")
        if response_model is None:
            return raw

        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)
        return response_model.model_validate(data)

    # -- Cost tracking --------------------------------------------------------

    def _track_cost(self, response_obj: Any) -> float:
        """Track cost via ``litellm.completion_cost`` and accumulate."""
        try:
            import litellm

            cost = float(litellm.completion_cost(completion_response=response_obj) or 0.0)
        except Exception:
            cost = 0.0
        self._cost_accumulated += cost
        return cost

    # -- Error classification -------------------------------------------------

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Return ``True`` if the exception warrants a transport retry."""
        exc_str = str(exc).lower()
        # HTTP 429 (rate limit)
        if "429" in exc_str or "rate" in exc_str:
            return True
        # HTTP 5xx
        if any(code in exc_str for code in ("500", "502", "503", "504")):
            return True
        # Network-level errors
        retryable_types = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        if isinstance(exc, retryable_types):
            return True
        # LiteLLM-specific retryable errors
        if "timeout" in exc_str or "connection" in exc_str:
            return True
        return False
