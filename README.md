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

## API Highlights

- `POST /game/new` create a game
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
