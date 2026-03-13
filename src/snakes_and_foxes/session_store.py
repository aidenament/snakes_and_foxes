from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis_async
from pydantic import BaseModel, ConfigDict

from snakes_and_foxes.domain.models import GameState
from snakes_and_foxes.settings import AppSettings

SESSION_COOKIE_NAME = "snakes_and_foxes_session"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_KEY_PREFIX = "snakes-and-foxes:session:"


def _token() -> str:
    return secrets.token_urlsafe(32)


class StoredGameSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    csrf_token: str
    state: GameState


class GameSessionStore(ABC):
    @abstractmethod
    async def create(self, state: GameState) -> StoredGameSession: ...

    @abstractmethod
    async def get(self, session_id: str) -> StoredGameSession | None: ...

    @abstractmethod
    async def save(self, session: StoredGameSession) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    async def aclose(self) -> None:
        return None


class InMemoryGameSessionStore(GameSessionStore):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, tuple[StoredGameSession, datetime]] = {}

    def _expires_at(self) -> datetime:
        return datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)

    def _prune(self) -> None:
        now = datetime.now(UTC)
        expired = [
            session_id
            for session_id, (_, expires_at) in self._sessions.items()
            if expires_at <= now
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

    async def create(self, state: GameState) -> StoredGameSession:
        session = StoredGameSession(
            session_id=_token(),
            csrf_token=_token(),
            state=state.model_copy(deep=True),
        )
        await self.save(session)
        return session

    async def get(self, session_id: str) -> StoredGameSession | None:
        self._prune()
        stored = self._sessions.get(session_id)
        if stored is None:
            return None
        session, _ = stored
        return session.model_copy(deep=True)

    async def save(self, session: StoredGameSession) -> None:
        self._sessions[session.session_id] = (session.model_copy(deep=True), self._expires_at())

    async def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


class RedisGameSessionStore(GameSessionStore):
    def __init__(
        self,
        *,
        redis_url: str | None = None,
        ttl_seconds: int,
        client: Any | None = None,
        key_prefix: str = SESSION_KEY_PREFIX,
    ) -> None:
        if client is None and not redis_url:
            raise ValueError("redis_url is required when no Redis client is provided.")
        self._client = (
            redis_async.from_url(redis_url, encoding="utf-8", decode_responses=True)
            if client is None
            else client
        )
        self._owns_client = client is None
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    async def create(self, state: GameState) -> StoredGameSession:
        session = StoredGameSession(
            session_id=_token(),
            csrf_token=_token(),
            state=state.model_copy(deep=True),
        )
        await self.save(session)
        return session

    async def get(self, session_id: str) -> StoredGameSession | None:
        payload = await self._client.get(self._key(session_id))
        if payload is None:
            return None
        return StoredGameSession.model_validate_json(payload)

    async def save(self, session: StoredGameSession) -> None:
        await self._client.setex(
            self._key(session.session_id),
            self._ttl_seconds,
            session.model_dump_json(),
        )

    async def delete(self, session_id: str) -> None:
        await self._client.delete(self._key(session_id))

    async def aclose(self) -> None:
        if self._owns_client and hasattr(self._client, "aclose"):
            await self._client.aclose()


def create_session_store(settings: AppSettings) -> GameSessionStore:
    if settings.session_backend == "memory":
        return InMemoryGameSessionStore(ttl_seconds=settings.session_ttl_seconds)
    if settings.session_backend == "redis":
        return RedisGameSessionStore(
            redis_url=settings.redis_url,
            ttl_seconds=settings.session_ttl_seconds,
        )
    raise ValueError(f"Unsupported session backend: {settings.session_backend}.")
