from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from snakes_and_foxes.domain.engine import apply_action, create_new_game
from snakes_and_foxes.domain.models import (
    ActionRequest,
    ActionResponse,
    CurrentGameResponse,
    NewGameRequest,
    NewGameResponse,
)
from snakes_and_foxes.session_store import (
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    GameSessionStore,
    StoredGameSession,
)
from snakes_and_foxes.settings import AppSettings

router = APIRouter(prefix="/api/game")


def _settings(request: Request) -> AppSettings:
    return request.app.state.settings


def _session_store(request: Request) -> GameSessionStore:
    return request.app.state.session_store


def _set_session_cookie(response: Response, request: Request, session: StoredGameSession) -> None:
    settings = _settings(request)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_id,
        httponly=True,
        max_age=settings.session_ttl_seconds,
        path="/",
        samesite="lax",
        secure=settings.is_production,
    )


def _verify_origin(request: Request) -> None:
    public_origin = _settings(request).public_origin
    origin = request.headers.get("origin")
    if origin is None or public_origin is None:
        return
    if origin.rstrip("/") != public_origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request origin.",
        )


def _verify_csrf_token(request: Request, session: StoredGameSession) -> None:
    token = request.headers.get(CSRF_HEADER_NAME)
    if token != session.csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )


async def _load_session(request: Request) -> StoredGameSession | None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return await _session_store(request).get(session_id)


async def _require_session(request: Request) -> StoredGameSession:
    session = await _load_session(request)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No live game session.")
    return session


@router.post("/new", response_model=NewGameResponse)
async def new_game(
    payload: NewGameRequest,
    request: Request,
    response: Response,
) -> NewGameResponse:
    _verify_origin(request)
    existing_session = await _load_session(request)
    if existing_session is not None:
        await _session_store(request).delete(existing_session.session_id)

    result = create_new_game(payload)
    session = await _session_store(request).create(result.state)
    _set_session_cookie(response, request, session)
    return NewGameResponse(state=result.state, result=result, csrf_token=session.csrf_token)


@router.get("/current", response_model=CurrentGameResponse)
async def current_game(request: Request, response: Response) -> CurrentGameResponse:
    session = await _require_session(request)
    await _session_store(request).save(session)
    _set_session_cookie(response, request, session)
    return CurrentGameResponse(state=session.state, csrf_token=session.csrf_token)


@router.post("/action", response_model=ActionResponse)
async def game_action(
    payload: ActionRequest,
    request: Request,
    response: Response,
) -> ActionResponse:
    _verify_origin(request)
    session = await _require_session(request)
    _verify_csrf_token(request, session)

    result = apply_action(session.state, payload.action)
    updated_session = session.model_copy(update={"state": result.state}, deep=True)
    await _session_store(request).save(updated_session)
    _set_session_cookie(response, request, updated_session)
    return ActionResponse(
        state=result.state,
        result=result,
        csrf_token=updated_session.csrf_token,
    )
