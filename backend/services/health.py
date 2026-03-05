from __future__ import annotations

from datetime import datetime, timezone

from config import ConfigStore
from providers.engine.router import EngineRouter
from providers.llm.router import LLMRouter
from schemas.api import HealthResponse, ProviderHealth
from services.openings import OpeningService


class HealthService:
    def __init__(
        self,
        config_store: ConfigStore,
        engine_router: EngineRouter,
        llm_router: LLMRouter,
        openings_service: OpeningService,
    ):
        self._config_store = config_store
        self._engine_router = engine_router
        self._llm_router = llm_router
        self._openings_service = openings_service

    async def get_health(self) -> HealthResponse:
        config = self._config_store.get()
        engine_statuses = await self._engine_router.get_provider_health()
        llm_statuses = await self._llm_router.get_provider_health()
        openings_health = self._openings_service.health()

        selected_engine = engine_statuses.get(config.engine.provider, ("down", "unknown provider"))
        selected_llm = llm_statuses.get("local", ("down", "local provider unavailable"))

        return HealthResponse(
            engine=ProviderHealth(status=selected_engine[0], detail=selected_engine[1]),
            llm=ProviderHealth(status=selected_llm[0], detail=selected_llm[1]),
            openings=ProviderHealth(status=openings_health.status, detail=openings_health.detail),
            timestamp=datetime.now(timezone.utc),
        )
