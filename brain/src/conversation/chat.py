"""LLM integration with multiple free and paid providers.

Supported providers (all use OpenAI-compatible chat/completions API):
  - groq:        Free tier, fast. Models: llama-3.3-70b-versatile, gemma2-9b-it
  - openrouter:  Free models available. Models: meta-llama/llama-3.3-70b-instruct:free
  - gemini:      Free tier via OpenAI-compatible endpoint. Models: gemini-2.0-flash
  - huggingface: Free Inference API. Models: meta-llama/Llama-3.3-70B-Instruct
  - anthropic:   Paid. Models: claude-sonnet-4-20250514
  - openai:      Paid. Models: gpt-4o
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from brain.src.config import Config
from brain.src.conversation.prompt_builder import build_system_prompt
from brain.src.logger import get_logger

log = get_logger("chat")

# Provider -> (base_url, api_key_env, default_model)
PROVIDERS: dict[str, tuple[str, str, str]] = {
    "groq": (
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "llama-3.3-70b-versatile",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "GEMINI_API_KEY",
        "gemini-2.0-flash",
    ),
    "huggingface": (
        "https://api-inference.huggingface.co/v1",
        "HF_API_KEY",
        "meta-llama/Llama-3.3-70B-Instruct",
    ),
    "openai": (
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "gpt-4o",
    ),
    "anthropic": (
        "",
        "ANTHROPIC_API_KEY",
        "claude-sonnet-4-20250514",
    ),
}


class ChatEngine:
    """Handles LLM calls via OpenAI-compatible APIs. Supports free providers."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._provider = config.llm.provider
        self._model = config.llm.model
        self._temperature = config.llm.temperature
        self._max_tokens = config.llm.max_tokens

        # Resolve provider config
        provider_info = PROVIDERS.get(self._provider)
        if provider_info:
            self._base_url = config.llm.base_url or provider_info[0]
            self._api_key_env = config.llm.api_key_env or provider_info[1]
        else:
            self._base_url = config.llm.base_url
            self._api_key_env = config.llm.api_key_env

        self._api_key = os.environ.get(self._api_key_env, "")

        # Fallback
        self._fallback_provider = config.llm.fallback_provider
        self._fallback_model = config.llm.fallback_model
        self._fallback_api_key_env = config.llm.fallback_api_key_env

        log.info(
            "chat_engine_init",
            provider=self._provider,
            model=self._model,
            has_key=bool(self._api_key),
        )

    async def chat(self, context: dict[str, Any]) -> dict[str, Any]:
        """Send context through LLM and return structured response."""
        system_prompt = build_system_prompt(context)
        user_text = context.get("input", "")

        try:
            raw = await self._call_llm(system_prompt, user_text)
            parsed = self._parse_response(raw)
            log.info("chat_success", provider=self._provider, response_len=len(raw))
            return parsed
        except Exception as e:
            log.warning("primary_llm_failed", provider=self._provider, error=str(e))

            # Try fallback
            if self._fallback_provider:
                try:
                    raw = await self._call_fallback(system_prompt, user_text)
                    parsed = self._parse_response(raw)
                    log.info("chat_fallback_success", provider=self._fallback_provider)
                    return parsed
                except Exception as e2:
                    log.error("fallback_llm_failed", provider=self._fallback_provider, error=str(e2))

            return {
                "response": "I'm having trouble connecting to my language model right now.",
                "actions": [],
                "facts_extracted": [],
                "associations": [],
                "topic": context.get("current_topic", ""),
            }

    async def _call_llm(self, system_prompt: str, user_text: str) -> str:
        """Call the primary LLM provider."""
        if self._provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_text, self._model)

        if not self._api_key:
            raise ValueError(f"{self._api_key_env} not set for provider '{self._provider}'")

        return await self._call_openai_compatible(
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
            system_prompt=system_prompt,
            user_text=user_text,
        )

    async def _call_fallback(self, system_prompt: str, user_text: str) -> str:
        """Call the fallback LLM provider."""
        if self._fallback_provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_text, self._fallback_model)

        fallback_info = PROVIDERS.get(self._fallback_provider)
        if not fallback_info:
            raise ValueError(f"Unknown fallback provider: {self._fallback_provider}")

        base_url = fallback_info[0]
        api_key_env = self._fallback_api_key_env or fallback_info[1]
        api_key = os.environ.get(api_key_env, "")

        if not api_key:
            raise ValueError(f"{api_key_env} not set for fallback '{self._fallback_provider}'")

        return await self._call_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=self._fallback_model,
            system_prompt=system_prompt,
            user_text=user_text,
        )

    async def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_text: str,
    ) -> str:
        """Call any OpenAI-compatible chat/completions API."""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"No choices in response from {base_url}")

        return choices[0].get("message", {}).get("content", "")

    async def _call_anthropic(self, system_prompt: str, user_text: str, model: str) -> str:
        """Call Anthropic's native API via the anthropic SDK."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_text}],
        )
        return response.content[0].text

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse plain text response. Extracts [ACTION] and [REMEMBER] tags."""
        raw = raw.strip()

        response_lines = []
        actions = []
        facts = []

        for line in raw.split("\n"):
            stripped = line.strip()

            if stripped.startswith("[ACTION]"):
                cmd = stripped[8:].strip()
                parts = cmd.split(None, 1)
                if parts:
                    action_type = parts[0]
                    target = parts[1] if len(parts) > 1 else ""
                    actions.append({"type": action_type, "target": target, "params": {}})

            elif stripped.startswith("[REMEMBER]"):
                fact_text = stripped[10:].strip()
                if fact_text:
                    facts.append({"content": fact_text, "category": "personal", "confidence": 0.8})

            else:
                response_lines.append(line)

        response_text = "\n".join(response_lines).strip()

        return {
            "response": response_text,
            "actions": actions,
            "facts_extracted": facts,
            "associations": [],
            "topic": "",
        }
