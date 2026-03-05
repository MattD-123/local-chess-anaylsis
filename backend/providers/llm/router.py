from __future__ import annotations

import asyncio

from config import ConfigStore
from providers.llm.base import LLMProvider
from providers.llm.ollama_local import OllamaLocalProvider
from providers.llm.prompt_builder import PromptBuilder


class LLMRouter:
    def __init__(self, config_store: ConfigStore):
        self._config_store = config_store
        self._lock = asyncio.Lock()
        self._prompt_builder = PromptBuilder()

        self._local: OllamaLocalProvider | None = None

        self._local_signature: tuple[str, str] | None = None

    async def _ensure_instances(self) -> None:
        config = self._config_store.get()

        async with self._lock:
            local_signature = (config.llm.local.base_url, config.llm.local.model)
            if self._local is None or self._local_signature != local_signature:
                self._local = OllamaLocalProvider(
                    base_url=config.llm.local.base_url,
                    model=config.llm.local.model,
                    prompt_builder=self._prompt_builder,
                )
                self._local_signature = local_signature

    async def get_active_provider(self) -> LLMProvider:
        await self._ensure_instances()
        return self._local  # type: ignore[return-value]

    async def get_local_provider(self) -> OllamaLocalProvider:
        await self._ensure_instances()
        return self._local  # type: ignore[return-value]

    async def get_provider_health(self) -> dict[str, tuple[str, str | None]]:
        await self._ensure_instances()
        local_status = await self._local.health() if self._local else ("down", "local LLM provider not initialized")
        return {"local": local_status}
