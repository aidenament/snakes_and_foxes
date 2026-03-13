# Snakes and Foxes

A browser adaptation of the Wheel of Time board game, served by FastAPI with a server-owned game session model.

## Stack

- Python 3.11+ with FastAPI
- SVG-driven browser UI with vanilla JavaScript
- Pure Python rules engine with cached board topology
- `uv` for dependency management and task execution
- In-memory sessions for local development, Redis-backed sessions for production

## Game Rules

- The board has a central hub plus seven concentric rings and sixteen spokes.
- You control two player pieces. Only one is active per turn.
- The active piece alternates each turn while both pieces are alive.
- A piece wins if it reaches the outer ring at least once and later returns to the center.
- Six dice are rolled each turn:
  - each piece keeps fair odds until that specific piece reaches the outer ring: roughly 33% `black_pip`, 33% `green_squiggle`, 33% `red_triangle`
  - once the active piece has already reached the outer ring, the return trip turns against the player: move symbols thin out and extra movement pips decay away over later rolls
- The active piece may move one edge per black pip:
  - from center to any node on the first ring
  - counter-clockwise on red rings
  - clockwise on green rings
  - either direction on the outer blue ring
  - inward one ring
  - outward one ring
- Players must spend the full movement total exactly. They may reverse along spokes, but ring movement must still follow each ring's direction.
- After player movement, the nearest foxes move first, then the nearest snakes.
- Enemies always path toward the active piece using board distance, not screen distance.
- If both player pieces are captured, the game is lost.

## Run Locally

```bash
uv sync
uv run uvicorn snakes_and_foxes.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Production Settings

Production mode is enabled with `APP_ENV=production`. In production:

- `ALLOWED_HOSTS` must be set to a comma-separated host allowlist.
- `SESSION_BACKEND` must be `redis`.
- `REDIS_URL` must point at the backing Redis instance.
- `PUBLIC_ORIGIN` should be set to the app's public origin if you want strict origin validation on browser POSTs.

Example:

```bash
APP_ENV=production \
ALLOWED_HOSTS=game.example.com \
SESSION_BACKEND=redis \
REDIS_URL=redis://localhost:6379/0 \
PUBLIC_ORIGIN=https://game.example.com \
uv run uvicorn snakes_and_foxes.app:app --host 0.0.0.0 --port 8000
```

## API Flow

- `POST /api/game/new` starts a fresh server-side session and sets an opaque HttpOnly session cookie.
- `GET /api/game/current` returns the resumable session state for the current browser session.
- `POST /api/game/action` accepts only the next action and requires `X-CSRF-Token`.

The browser never sends authoritative `GameState` back to the server.

## Quality Checks

```bash
uv run pytest
uv run ruff check
```

## Local Benchmark

Use the deterministic engine benchmark to spot large regressions without turning timing into a test gate:

```bash
uv run python scripts/profile_engine.py
```

## Project Layout

- `src/snakes_and_foxes/app.py`: app factory, middleware wiring, and HTML entrypoint
- `src/snakes_and_foxes/api/routes.py`: session-backed JSON API routes
- `src/snakes_and_foxes/domain/`: rules engine, models, and topology cache
- `src/snakes_and_foxes/session_store.py`: in-memory and Redis session backends
- `src/snakes_and_foxes/templates/index.html`: app shell
- `src/snakes_and_foxes/static/`: CSS, fonts, and browser code
- `scripts/profile_engine.py`: local engine benchmark
- `tests/`: API, store, and domain tests
