"""Claude API integration with structured output parsing."""

from __future__ import annotations

import json
import os
from typing import Any

from brain.src.config import Config
from brain.src.conversation.prompt_builder import build_system_prompt
from brain.src.logger import get_logger

log = get_logger("chat")


class ChatEngine:
    """Handles LLM calls and response parsing."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: Any = None
        self._provider = config.llm.provider

    async def _get_client(self) -> Any:
        if self._client:
            return self._client

        if self._provider == "anthropic":
            try:
                import anthropic
                api_key = os.environ.get(self._config.llm.api_key_env, "")
                if not api_key:
                    raise ValueError(f"{self._config.llm.api_key_env} not set")
                self._client = anthropic.AsyncAnthropic(api_key=api_key)
                return self._client
            except ImportError:
                log.warning("anthropic_not_installed", fallback=self._config.llm.fallback_provider)
                self._provider = self._config.llm.fallback_provider

        if self._provider == "openai":
            try:
                import openai
                api_key = os.environ.get("OPENAI_API_KEY", "")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                self._client = openai.AsyncOpenAI(api_key=api_key)
                return self._client
            except ImportError:
                raise RuntimeError("No LLM provider available. Install anthropic or openai.")

        raise RuntimeError(f"Unknown LLM provider: {self._provider}")

    async def chat(self, context: dict[str, Any]) -> dict[str, Any]:
        """Send context through LLM and return structured response."""
        system_prompt = build_system_prompt(context)
        user_text = context.get("input", "")

        try:
            raw = await self._call_llm(system_prompt, user_text)
            return self._parse_response(raw)
        except Exception as e:
            log.error("chat_failed", error=str(e))
            return {
                "response": "I'm having trouble processing that right now.",
                "actions": [],
                "facts_extracted": [],
                "associations": [],
                "topic": context.get("current_topic", ""),
            }

    async def _call_llm(self, system_prompt: str, user_text: str) -> str:
        client = await self._get_client()

        if self._provider == "anthropic":
            response = await client.messages.create(
                model=self._config.llm.model,
                max_tokens=self._config.llm.max_tokens,
                temperature=self._config.llm.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_text}],
            )
            return response.content[0].text

        if self._provider == "openai":
            response = await client.chat.completions.create(
                model=self._config.llm.fallback_model,
                max_tokens=self._config.llm.max_tokens,
                temperature=self._config.llm.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
            )
            return response.choices[0].message.content or ""

        raise RuntimeError(f"Unknown provider: {self._provider}")

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse structured JSON from LLM response. Falls back to plain text."""
        # Try to extract JSON from the response
        raw = raw.strip()

        # Handle markdown code blocks
        if raw.startswith("```"):
            lines = raw.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                if line.startswith("```") and in_block:
                    break
                if in_block:
                    json_lines.append(line)
            raw = "\n".join(json_lines)

        try:
            parsed = json.loads(raw)
            return {
                "response": parsed.get("response", raw),
                "actions": parsed.get("actions", []),
                "facts_extracted": parsed.get("facts_extracted", []),
                "associations": parsed.get("associations", []),
                "topic": parsed.get("topic", ""),
            }
        except json.JSONDecodeError:
            # LLM returned plain text instead of JSON
            return {
                "response": raw,
                "actions": [],
                "facts_extracted": [],
                "associations": [],
                "topic": "",
            }
