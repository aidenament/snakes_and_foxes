from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from snakes_and_foxes.app import create_app
from snakes_and_foxes.session_store import InMemoryGameSessionStore
from snakes_and_foxes.settings import AppSettings


@pytest.fixture
def settings() -> AppSettings:
    return AppSettings(
        app_env="development",
        session_backend="memory",
        session_ttl_seconds=60 * 60,
        max_request_body_bytes=16_384,
    )


@pytest.fixture
def session_store(settings: AppSettings) -> InMemoryGameSessionStore:
    return InMemoryGameSessionStore(ttl_seconds=settings.session_ttl_seconds)


@pytest.fixture
def client(
    settings: AppSettings,
    session_store: InMemoryGameSessionStore,
) -> Iterator[TestClient]:
    with TestClient(create_app(settings=settings, session_store=session_store)) as test_client:
        yield test_client
