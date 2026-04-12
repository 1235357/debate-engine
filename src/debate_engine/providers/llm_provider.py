"""LLM Provider wrapping LiteLLM with retry logic, structured output, and cost tracking."""

from __future__ import annotations
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal
from pydantic import BaseModel, ValidationError
from .config import ProviderConfig, ProviderMode

logger = logging.getLogger(__name__)


@dataclass
class CallResult:
    status: Literal["SUCCESS", "PARSE_FAILED", "ROLE_FAILED"] = "SUCCESS"
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    model_used: str = ""
    parse_attempts: int = 1
    raw_response: str | None = None
    error_message: str | None = None


class LLMProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._cost_accumulated: float = 0.0
        self._call_count: int = 0
        self._instructor_available: bool | None = None

    @property
    def cost_accumulated(self) -> float:
        return self._cost_accumulated

    @property
    def call_count(self) -> int:
        return self._call_count

    async def call(self, messages, system_prompt=None, response_model=None,
                   role_type="critic", temperature=0.3):
        provider, model = self._get_model_for_role(role_type)
        model_display = f"{provider}/{model}"
        start = time.monotonic()
        raw_response = None
        parse_attempts = 0
        status = "ROLE_FAILED"
        error_message = None
        parsed = None
        cost_usd = 0.0
        litellm_params = self._build_litellm_params(provider, model, messages, system_prompt, temperature)

        for transport_attempt in range(1, self.config.max_transport_retries + 2):
            backoff = 2 ** (transport_attempt - 1)
            if transport_attempt > 1:
                await asyncio.sleep(backoff)
            try:
                response = await asyncio.wait_for(
                    self._acompletion(litellm_params, response_model),
                    timeout=self.config.timeout_seconds)
                self._call_count += 1
                if isinstance(response, tuple):
                    raw_response, response_obj = response
                else:
                    parsed = response
                    raw_response = response.model_dump_json()
                    response_obj = None
                cost_usd = self._track_cost(response_obj)
                if parsed is not None:
                    status = "SUCCESS"
                    parse_attempts = 1
                    break
                for parse_attempt in range(1, self.config.max_parse_retries + 2):
                    parse_attempts = parse_attempt
                    try:
                        parsed = self._parse_json_response(raw_response, response_model)
                        status = "SUCCESS"
                        break
                    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                        if parse_attempt <= self.config.max_parse_retries:
                            repair_messages = list(messages)
                            repair_messages.append({"role": "user", "content": f"Parse error: {exc}. Fix your JSON."})
                            new_msgs = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + repair_messages
                            litellm_params["messages"] = new_msgs
                            try:
                                repair_resp = await asyncio.wait_for(self._acompletion(litellm_params, None), timeout=self.config.timeout_seconds)
                                self._call_count += 1
                                if isinstance(repair_resp, tuple):
                                    raw_response, response_obj = repair_resp
                                    cost_usd += self._track_cost(response_obj)
                                else:
                                    raw_response = str(repair_resp)
                            except Exception:
                                break
                        else:
                            error_message = str(exc)
                if status != "SUCCESS":
                    status = "PARSE_FAILED"
                break
            except asyncio.TimeoutError:
                error_message = f"Timeout after {self.config.timeout_seconds}s"
            except Exception as exc:
                error_message = str(exc)
                if not self._is_retryable(exc):
                    break

        latency_ms = (time.monotonic() - start) * 1000
        return parsed if parsed is not None else raw_response, CallResult(
            status=status, cost_usd=cost_usd, latency_ms=latency_ms,
            model_used=model_display, parse_attempts=parse_attempts,
            raw_response=raw_response, error_message=error_message)

    def _get_model_for_role(self, role_type):
        cfg = self.config
        if role_type == "judge":
            return cfg.effective_judge_provider, cfg.effective_judge_model
        if cfg.mode == ProviderMode.BALANCED and role_type == "devil_advocate":
            if cfg.backup_provider and cfg.backup_model:
                return cfg.backup_provider, cfg.backup_model
        return cfg.primary_provider, cfg.primary_model

    @staticmethod
    def _build_litellm_params(provider, model, messages, system_prompt, temperature):
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        return {"model": f"{provider}/{model}" if "/" not in model else model, "messages": full_messages, "temperature": temperature}

    async def _acompletion(self, params, response_model):
        import litellm
        if response_model is not None and self._check_instructor():
            return await self._acompletion_with_instructor(params, response_model)
        response = await litellm.acompletion(**params)
        return response.choices[0].message.content or "", response

    def _check_instructor(self):
        if self._instructor_available is None:
            try:
                import instructor
                self._instructor_available = True
            except ImportError:
                self._instructor_available = False
        return self._instructor_available

    async def _acompletion_with_instructor(self, params, response_model):
        import instructor
        import litellm
        client = instructor.from_litellm(litellm.AsyncOpenAI())
        model = params.pop("model")
        messages = params.pop("messages")
        temperature = params.pop("temperature", 0.3)
        return await client.chat.completions.create(model=model, messages=messages, temperature=temperature, response_model=response_model, **params)

    @staticmethod
    def _parse_json_response(raw, response_model):
        if raw is None:
            raise ValueError("Raw response is None")
        if response_model is None:
            return raw
        text = raw.strip()
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return response_model.model_validate(json.loads(text))

    def _track_cost(self, response_obj):
        try:
            import litellm
            cost = litellm.completion_cost(completion_response=response_obj)
        except Exception:
            cost = 0.0
        self._cost_accumulated += cost
        return cost

    @staticmethod
    def _is_retryable(exc):
        exc_str = str(exc).lower()
        if "429" in exc_str or "rate" in exc_str:
            return True
        if any(c in exc_str for c in ("500", "502", "503", "504")):
            return True
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return True
        if "timeout" in exc_str or "connection" in exc_str:
            return True
        return False