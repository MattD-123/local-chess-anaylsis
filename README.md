# Chess App (FastAPI + React)
Copyright (C) 2026 Matthew Doe

An interactive full-stack chess app with:
- Local Stockfish engine integration
- Ollama-powered live commentary
- Server-Sent Events (SSE) streaming
- Opening detection and opening statistics
- Game history and post-game analysis
- PGN import/export tooling
- Interactive analysis board with eval graph and blunder review mode
- Runtime settings via API-backed config

## Tech Stack

- Backend: FastAPI, Python, SQLite, python-chess
- Frontend: React (Vite), Tailwind CSS
- AI/Engine: Stockfish (local binary), Ollama (local service)

## Repository Layout

```text
backend/     FastAPI API, game services, providers, database layer, tests
frontend/    React UI, state provider, board and commentary components
config.yaml  Runtime-editable app configuration
```

## Prerequisites

- Python 3.12+
- Node.js 22 LTS+
- Stockfish binary installed locally
- Ollama installed and running with a downloaded model

## Quick Start

### 1) Configure

Edit `config.yaml`:

- `engine.local.path`: absolute path to your Stockfish executable
- `llm.local.model`: installed Ollama model name
- `engine.local.pool_size`: number of parallel Stockfish workers (default `3`)
- `runtime.max_active_sessions`: concurrent active game cap (default `100`)

### 2) Simplest Run (Windows)

From repo root:

```powershell
.\scripts\dev.ps1
```

What it does:
- Creates backend `.venv` and installs Python deps if missing
- Runs `npm install` if `frontend/node_modules` is missing
- Starts backend and frontend in separate PowerShell windows

If you want to force dependency reinstall:

```powershell
.\scripts\dev.ps1 -ForceInstall
```

### 3) Manual Run (cross-platform)

Run backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn main:app --reload --port 8000
```

Run frontend:

```powershell
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:5173` and backend to `http://127.0.0.1:8000`.

## LAN Multiplayer (Single Host)

To make the app available to other devices on your local network:

1. Build and serve from backend using the LAN script:

```powershell
.\scripts\start-lan.ps1
```

2. Share the LAN URL shown by the script:

```text
http://<host-ip>:8000
```

3. Ensure firewall allows inbound TCP 8000:

```powershell
netsh advfirewall firewall add rule name="Chess LAN 8000" dir=in action=allow protocol=TCP localport=8000
```

### Multi-user expectations

- Designed for trusted LAN use.
- Multiple players can run independent games concurrently.
- Per-game settings are isolated by `game_id` (no cross-user setting collisions).
- Default local engine pool: `pool_size: 3` (tune in `config.yaml`).

## API Highlights

- `POST /game/new` create a game
- `POST /game/settings` update options for one active game
- `POST /game/move` submit player move
- `GET /game/commentary?game_id=...` SSE stream (`commentary_chunk`, `engine_move`, `opening_update`, etc.)
- `GET /game/history` recent games
- `GET /game/analysis` game summary
- `POST /game/import-pgn` import a PGN as a reviewable game
- `GET /game/export-pgn?game_id=...` export a game as PGN text
- `GET /openings/stats` opening performance
- `GET /config` and `POST /config` runtime settings
- `GET /health` provider/openings health status

## Openings Data

Openings are bootstrapped automatically on startup from:
- https://github.com/lichess-org/chess-openings

To keep this repository lean, `backend/database/openings.db` is intentionally excluded.

## Health and Troubleshooting

- If Stockfish path is invalid, engine health will report `down`.
- If Ollama is unavailable, LLM health will report `down`.
- Check `GET /health` for current status and error details.
- If users experience delayed bot replies under load, check `/health` engine metrics:
  - `queue_depth`
  - `avg_wait_ms`
  - `queue_timeout_count`
- Increase `engine.local.pool_size` if CPU headroom allows.
- If queue timeouts increase, lower depth/think time in per-game settings.
- Stale sessions are cleaned automatically (`runtime.session_ttl_hours` and `runtime.cleanup_interval_seconds`).

## Testing

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

```powershell
cd frontend
npm test
```

## License

Licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See `license.txt`.
