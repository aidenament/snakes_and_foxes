from __future__ import annotations

import pytest

from snakes_and_foxes.domain.engine import create_new_game
from snakes_and_foxes.domain.models import NewGameRequest
from snakes_and_foxes.session_store import (
    SESSION_KEY_PREFIX,
    InMemoryGameSessionStore,
    RedisGameSessionStore,
)


class FakeRedisClient:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}
        self.setex_calls: list[tuple[str, int, str]] = []
        self.delete_calls: list[str] = []

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def setex(self, key: str, ttl_seconds: int, payload: str) -> None:
        self.setex_calls.append((key, ttl_seconds, payload))
        self.storage[key] = payload

    async def delete(self, key: str) -> None:
        self.delete_calls.append(key)
        self.storage.pop(key, None)


@pytest.mark.anyio
async def test_in_memory_store_round_trips_sessions():
    store = InMemoryGameSessionStore(ttl_seconds=60)
    session = await store.create(create_new_game(NewGameRequest(seed=7)).state)

    loaded = await store.get(session.session_id)
    assert loaded is not None
    assert loaded.state.seed == 7

    updated = loaded.model_copy(deep=True)
    updated.state.turn_number = 3
    await store.save(updated)

    saved = await store.get(session.session_id)
    assert saved is not None
    assert saved.state.turn_number == 3

    await store.delete(session.session_id)
    assert await store.get(session.session_id) is None


@pytest.mark.anyio
async def test_redis_store_round_trips_and_uses_ttl():
    fake_client = FakeRedisClient()
    store = RedisGameSessionStore(client=fake_client, ttl_seconds=90)

    session = await store.create(create_new_game(NewGameRequest(seed=11)).state)
    loaded = await store.get(session.session_id)

    assert loaded is not None
    assert loaded.state.seed == 11
    assert fake_client.setex_calls
    key, ttl_seconds, _ = fake_client.setex_calls[-1]
    assert key == f"{SESSION_KEY_PREFIX}{session.session_id}"
    assert ttl_seconds == 90

    await store.delete(session.session_id)
    assert fake_client.delete_calls == [f"{SESSION_KEY_PREFIX}{session.session_id}"]
