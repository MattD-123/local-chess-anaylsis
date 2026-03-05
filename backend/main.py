from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import ConfigStore
from database.repo import ChessRepository
from database.session import SQLiteSessionManager
from logging_config import configure_logging, set_request_id
from providers.engine.router import EngineRouter
from providers.llm.router import LLMRouter
from schemas.api import (
    AnalysisResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    HealthResponse,
    HintResponse,
    GameSettingsRequest,
    GameSettingsResponse,
    MoveRequest,
    MoveResponse,
    NewGameRequest,
    NewGameResponse,
    OpeningStatsResponse,
    PgnImportRequest,
    PgnImportResponse,
    ResignRequest,
    ResignResponse,
)
from services.analysis import AnalysisService
from services.commentary import CommentaryBus
from services.game import GameService
from services.health import HealthService
from services.openings import OpeningService

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# python-chess engine subprocess management requires Proactor loop on Windows.
if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    config_store = ConfigStore()
    config_store.load()

    repo = ChessRepository(SQLiteSessionManager())
    repo.initialize()

    engine_router = EngineRouter(config_store)
    llm_router = LLMRouter(config_store)
    commentary_bus = CommentaryBus()
    openings_service = OpeningService(repo)
    await openings_service.bootstrap_if_needed()

    game_service = GameService(
        config_store=config_store,
        repo=repo,
        engine_router=engine_router,
        llm_router=llm_router,
        opening_service=openings_service,
        commentary_bus=commentary_bus,
    )
    analysis_service = AnalysisService(repo=repo, llm_router=llm_router)
    health_service = HealthService(
        config_store=config_store,
        engine_router=engine_router,
        llm_router=llm_router,
        openings_service=openings_service,
    )

    app.state.config_store = config_store
    app.state.repo = repo
    app.state.engine_router = engine_router
    app.state.llm_router = llm_router
    app.state.openings_service = openings_service
    app.state.game_service = game_service
    app.state.analysis_service = analysis_service
    app.state.health_service = health_service

    try:
        yield
    finally:
        await engine_router.close()


app = FastAPI(title="Chess App API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id")
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id or "generated"
    return response


def _game_service(request: Request) -> GameService:
    return request.app.state.game_service


def _analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def _health_service(request: Request) -> HealthService:
    return request.app.state.health_service


def _config_store(request: Request) -> ConfigStore:
    return request.app.state.config_store


@app.post("/game/new", response_model=NewGameResponse)
async def create_game(payload: NewGameRequest, request: Request) -> NewGameResponse:
    service = _game_service(request)
    try:
        return await service.new_game(
            payload.player_color,
            payload.config_overrides,
            payload.options,
        )
    except Exception as exc:
        logger.exception("Failed to create game")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/game/move", response_model=MoveResponse)
async def submit_move(payload: MoveRequest, request: Request) -> MoveResponse:
    service = _game_service(request)
    try:
        return await service.submit_player_move(payload.game_id, payload.move)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to submit move")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.get("/game/commentary")
async def commentary_stream(game_id: str, request: Request):
    service = _game_service(request)
    bus = service.get_bus()

    async def event_generator() -> AsyncIterator[str]:
        async for event in bus.stream(game_id):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/game/hint", response_model=HintResponse)
async def game_hint(game_id: str, request: Request) -> HintResponse:
    service = _game_service(request)
    try:
        return await service.get_hint(game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/game/resign", response_model=ResignResponse)
async def resign(payload: ResignRequest, request: Request) -> ResignResponse:
    service = _game_service(request)
    try:
        return await service.resign(payload.game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/game/analysis", response_model=AnalysisResponse)
async def game_analysis(game_id: str, request: Request) -> AnalysisResponse:
    service = _analysis_service(request)
    try:
        return await service.get_analysis(game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/game/history")
async def game_history(request: Request):
    service = _game_service(request)
    return service.get_history()


@app.post("/game/settings", response_model=GameSettingsResponse)
async def update_game_settings(payload: GameSettingsRequest, request: Request) -> GameSettingsResponse:
    service = _game_service(request)
    try:
        return await service.update_game_settings(payload.game_id, payload.options)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to update game settings")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/game/import-pgn", response_model=PgnImportResponse)
async def import_pgn(payload: PgnImportRequest, request: Request) -> PgnImportResponse:
    service = _game_service(request)
    try:
        return await service.import_pgn(payload.pgn, payload.player_color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to import PGN")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.get("/game/export-pgn", response_class=PlainTextResponse)
async def export_pgn(game_id: str, request: Request) -> PlainTextResponse:
    service = _game_service(request)
    try:
        pgn_text = service.export_pgn(game_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(
        pgn_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{game_id}.pgn"'},
    )


@app.get("/openings/stats", response_model=OpeningStatsResponse)
async def opening_stats(request: Request) -> OpeningStatsResponse:
    service = _game_service(request)
    return service.get_opening_stats()


@app.get("/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    store = _config_store(request)
    return ConfigResponse(config=store.get_dict(resolved=True))


@app.post("/config", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdateRequest, request: Request) -> ConfigResponse:
    store = _config_store(request)
    try:
        store.update(payload.patch)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConfigResponse(config=store.get_dict(resolved=True))


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    service = _health_service(request)
    return await service.get_health()


@app.get("/", include_in_schema=False)
async def frontend_index():
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return PlainTextResponse(
        "Frontend build not found. Run 'cd frontend && npm run build'.",
        status_code=503,
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_spa_fallback(full_path: str):
    # Let API/documentation routes continue to use their own handlers.
    reserved_prefixes = ("game/", "openings/", "config", "health", "docs", "redoc", "openapi.json")
    if full_path.startswith(reserved_prefixes):
        raise HTTPException(status_code=404, detail="Not found")

    candidate = FRONTEND_DIST / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)

    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return PlainTextResponse(
        "Frontend build not found. Run 'cd frontend && npm run build'.",
        status_code=503,
    )
