from __future__ import annotations

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles

from snakes_and_foxes.settings import AppSettings

PRODUCTION_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestBodyTooLarge(Exception):
    """Raised when a JSON request body exceeds the configured byte limit."""


class JSONBodyLimitMiddleware:
    def __init__(self, app, *, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method = scope.get("method", "").upper()
        content_type = headers.get("content-type", "")
        if method not in {"POST", "PUT", "PATCH"} or "application/json" not in content_type:
            await self.app(scope, receive, send)
            return

        content_length = headers.get("content-length")
        if content_length is not None and int(content_length) > self.max_body_bytes:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] != "http.request":
                return message

            received += len(message.get("body", b""))
            if received > self.max_body_bytes:
                raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
            await response(scope, receive, send)


class ResponseHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: AppSettings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request, call_next) -> Response:
        response = await call_next(request)
        self._apply_cache_headers(request.url.path, response)
        if self._settings.is_production:
            for header, value in PRODUCTION_SECURITY_HEADERS.items():
                response.headers.setdefault(header, value)
        return response

    def _apply_cache_headers(self, path: str, response: Response) -> None:
        if path.startswith("/static/"):
            response.headers["Cache-Control"] = (
                "public, max-age=86400" if self._settings.is_production else "no-store"
            )
            return

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type or "application/json" in content_type:
            response.headers.setdefault("Cache-Control", "no-store")


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
        return response
