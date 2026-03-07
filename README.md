# Snakes and Foxes

A polished browser adaptation of the Wheel of Time board game, served by FastAPI and managed with `uv`.

## Stack

- Python + FastAPI backend
- Canvas-based browser UI
- Pure Python rules engine with graph-based enemy pathfinding
- `uv` for dependency management, locking, and task execution

## Game Rules

- The board has six concentric circles.
- The center is a single node. Every outer circle has ten nodes.
- You control two player pieces. Only one is active per turn.
- The active piece alternates each turn while both pieces are alive.
- A piece wins if it reaches the outer ring at least once and later returns to the center.
- Six dice are rolled each turn:
  - `black_pip` results grant movement steps
  - `red_triangle` results activate foxes
  - `green_squiggle` results activate snakes
- The active piece may move one edge per black pip:
  - from center to any node on the first ring
  - along the current ring in that ring's direction
  - inward one ring
  - outward one ring
- After player movement, the nearest foxes move first, then the nearest snakes.
- Enemies always path toward the active piece using board distance, not screen distance.
- If both player pieces are captured, the game is lost.

## Run Locally

```bash
uv sync
uv run uvicorn snakes_and_foxes.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Quality Checks

```bash
uv run pytest
uv run ruff check
```

## Project Layout

- `src/snakes_and_foxes/app.py`: FastAPI app and HTML entrypoint
- `src/snakes_and_foxes/api/routes.py`: JSON API routes
- `src/snakes_and_foxes/domain/`: rules engine and models
- `src/snakes_and_foxes/templates/index.html`: app shell
- `src/snakes_and_foxes/static/`: CSS and browser code
- `tests/`: domain and API tests

## Git History Cleanup

This repo used to track `venv/` and Python cache artifacts. The cleanup process is:

```bash
git fetch --all --prune
git reset --hard origin/main
```

If your local clone predates the history rewrite, the simplest recovery path is to reclone the repository.
