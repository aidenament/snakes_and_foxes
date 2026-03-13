from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from snakes_and_foxes.api.routes import router as api_router
from snakes_and_foxes.middleware import (
    CachedStaticFiles,
    JSONBodyLimitMiddleware,
    ResponseHeadersMiddleware,
)
from snakes_and_foxes.session_store import GameSessionStore, create_session_store
from snakes_and_foxes.settings import AppSettings

BASE_DIR = Path(__file__).resolve().parent


def create_app(
    settings: AppSettings | None = None,
    session_store: GameSessionStore | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_settings.validate()
    store = session_store or create_session_store(resolved_settings)
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await store.aclose()

    app = FastAPI(
        title="Snakes and Foxes",
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.session_store = store

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(resolved_settings.trusted_hosts))
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        JSONBodyLimitMiddleware,
        max_body_bytes=resolved_settings.max_request_body_bytes,
    )
    app.add_middleware(ResponseHeadersMiddleware, settings=resolved_settings)

    app.include_router(api_router)
    app.mount("/static", CachedStaticFiles(directory=BASE_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "index.html", {"request": request})

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
