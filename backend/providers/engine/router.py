from __future__ import annotations

import asyncio

from config import ConfigStore
from providers.engine.base import ChessEngine
from providers.engine.stockfish_api import StockfishAPIProvider
from providers.engine.stockfish_local import StockfishLocalProvider


class EngineRouter:
    def __init__(self, config_store: ConfigStore):
        self._config_store = config_store
        self._lock = asyncio.Lock()
        self._local: StockfishLocalProvider | None = None
        self._api: StockfishAPIProvider | None = None
        self._local_path: str | None = None
        self._api_url: str | None = None

    async def _ensure_instances(self) -> None:
        config = self._config_store.get()

        async with self._lock:
            local_cfg = config.engine.local
            if self._local is None or self._local_path != local_cfg.path:
                if self._local is not None:
                    await self._local.close()
                self._local = StockfishLocalProvider(
                    path=local_cfg.path,
                    think_time_ms=local_cfg.think_time_ms,
                    default_depth=local_cfg.depth,
                )
                self._local_path = local_cfg.path

            api_cfg = config.engine.api
            if self._api is None or self._api_url != api_cfg.url:
                self._api = StockfishAPIProvider(base_url=api_cfg.url)
                self._api_url = api_cfg.url

            try:
                await self._local.set_skill_level(local_cfg.skill_level)
            except Exception:
                # Skill setting should not crash provider routing when local engine is unavailable.
                pass
            if self._api is not None:
                await self._api.set_skill_level(local_cfg.skill_level)

    async def get_active_engine(self) -> ChessEngine:
        await self._ensure_instances()
        config = self._config_store.get()
        if config.engine.provider == "api":
            return self._api  # type: ignore[return-value]
        return self._local  # type: ignore[return-value]

    async def get_local_engine(self) -> StockfishLocalProvider:
        await self._ensure_instances()
        return self._local  # type: ignore[return-value]

    async def get_provider_health(self) -> dict[str, tuple[str, str | None]]:
        await self._ensure_instances()
        local_status = await self._local.health() if self._local else ("down", "local provider not initialized")
        api_status = await self._api.health() if self._api else ("down", "api provider not initialized")
        return {"local": local_status, "api": api_status}

    async def close(self) -> None:
        if self._local is not None:
            await self._local.close()
        if self._api is not None:
            await self._api.close()
