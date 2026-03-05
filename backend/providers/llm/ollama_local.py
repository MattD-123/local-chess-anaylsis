from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from providers.llm.base import LLMProvider
from providers.llm.prompt_builder import PromptBuilder
from schemas.domain import CommentaryContext, CompletedGame, HintContext, OpeningInfo

logger = logging.getLogger(__name__)


class OllamaLocalProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, prompt_builder: PromptBuilder):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._prompt_builder = prompt_builder

    async def _stream_prompt(self, prompt: str) -> AsyncIterator[str]:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = chunk.get("message") or {}
                    content = message.get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break

    async def _single_response(self, prompt: str) -> str:
        parts: list[str] = []
        async for chunk in self._stream_prompt(prompt):
            parts.append(chunk)
        return "".join(parts).strip()

    async def get_commentary(self, context: CommentaryContext) -> AsyncIterator[str]:
        prompt = self._prompt_builder.build_commentary_prompt(context)
        return self._stream_prompt(prompt)

    async def get_hint(self, context: HintContext) -> str:
        prompt = self._prompt_builder.build_hint_prompt(context)
        return await self._single_response(prompt)

    async def get_opening_commentary(self, opening: OpeningInfo, side: str) -> AsyncIterator[str]:
        prompt = self._prompt_builder.build_opening_commentary_prompt(opening, side, persona="coach")
        return self._stream_prompt(prompt)

    async def get_game_summary(self, game: CompletedGame) -> str:
        prompt = self._prompt_builder.build_game_summary_prompt(game)
        return await self._single_response(prompt)

    async def health(self) -> tuple[str, str | None]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()

            models = payload.get("models") or []
            names: set[str] = set()
            for item in models:
                name = (item.get("name") or "").strip()
                if not name:
                    continue
                names.add(name)
                names.add(name.split(":", 1)[0])

            target = self._model.strip()
            target_base = target.split(":", 1)[0]
            if target not in names and target_base not in names:
                detail = (
                    f"Configured Ollama model '{self._model}' is not available. "
                    "Run: ollama pull <model> and update config.yaml."
                )
                return "degraded", detail

            return "ok", None
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return "degraded", str(exc)
