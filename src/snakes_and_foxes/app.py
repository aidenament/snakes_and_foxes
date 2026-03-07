from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from snakes_and_foxes.api.routes import router as api_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Snakes and Foxes")
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
