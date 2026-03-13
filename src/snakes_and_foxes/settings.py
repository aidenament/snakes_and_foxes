from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from os import environ

DEFAULT_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "testserver")
VALID_APP_ENVS = {"development", "production", "test"}
VALID_SESSION_BACKENDS = {"memory", "redis"}


def _normalize_origin(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    return normalized or None


def _parse_csv(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_env: str = "development"
    allowed_hosts: tuple[str, ...] = ()
    public_origin: str | None = None
    session_backend: str = "memory"
    redis_url: str | None = None
    session_ttl_seconds: int = 60 * 60 * 24
    max_request_body_bytes: int = 16_384

    @classmethod
    def from_env(cls, source: Mapping[str, str] | None = None) -> AppSettings:
        values = environ if source is None else source
        settings = cls(
            app_env=values.get("APP_ENV", "development").strip().lower(),
            allowed_hosts=_parse_csv(values.get("ALLOWED_HOSTS")),
            public_origin=_normalize_origin(values.get("PUBLIC_ORIGIN")),
            session_backend=values.get("SESSION_BACKEND", "memory").strip().lower(),
            redis_url=values.get("REDIS_URL"),
            session_ttl_seconds=int(values.get("SESSION_TTL_SECONDS", str(60 * 60 * 24))),
            max_request_body_bytes=int(values.get("MAX_REQUEST_BODY_BYTES", "16384")),
        )
        settings.validate()
        return settings

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production

    @property
    def trusted_hosts(self) -> tuple[str, ...]:
        if self.allowed_hosts:
            return self.allowed_hosts
        return DEFAULT_ALLOWED_HOSTS

    def validate(self) -> None:
        if self.app_env not in VALID_APP_ENVS:
            raise ValueError(f"APP_ENV must be one of {sorted(VALID_APP_ENVS)}.")
        if self.session_backend not in VALID_SESSION_BACKENDS:
            raise ValueError(
                f"SESSION_BACKEND must be one of {sorted(VALID_SESSION_BACKENDS)}."
            )
        if self.session_ttl_seconds <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be greater than zero.")
        if self.max_request_body_bytes <= 0:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be greater than zero.")
        if self.is_production and not self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS must be configured in production.")
        if self.is_production and self.session_backend != "redis":
            raise ValueError("SESSION_BACKEND must be set to 'redis' in production.")
        if self.session_backend == "redis" and not self.redis_url:
            raise ValueError("REDIS_URL must be configured when SESSION_BACKEND=redis.")
