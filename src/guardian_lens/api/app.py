"""Application factory — wiring, error envelope, request tracing.

Every error leaves through one translator producing the TRD 10.8 envelope,
so no handler can leak an internal exception, SQL error or stack trace to
a client (BACKEND_CODING_RULES 12). Unexpected exceptions are logged with
their trace_id and surface as a generic GL-5000.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from guardian_lens.api.routes import (
    audit as audit_routes,
    auth as auth_routes,
    config as config_routes,
    discovery as discovery_routes,
    health as health_routes,
    ingest as ingest_routes,
    live as live_routes,
    reports as reports_routes,
    review as review_routes,
)
from guardian_lens.core.errors import GuardianError, envelope
from guardian_lens.core.logging import (
    configure_logging,
    get_logger,
    log_event,
    tenant_var,
    trace_id_var,
    user_id_var,
)
from guardian_lens.core.settings import Settings, load_settings
from guardian_lens.repositories.evidence import FilesystemEvidenceStore
from guardian_lens.services.identity import IdentityService
from guardian_lens.services.live_preview import LivePreviewStore
from guardian_lens.services.ptz_commands import PtzCommandStore
from guardian_lens.services.sealer import build_sealer
from guardian_lens.services.self_service import SelfServiceAuthService
from guardian_lens.services.tokens import TokenService
from guardian_lens.tenancy.registry import TenantRegistry
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["create_app", "LoginRateLimiter"]

_log = get_logger("guardian_lens.api")


class LoginRateLimiter:
    """In-memory sliding window, per key (IP). Sufficient for the MVP's
    single process (TRD 12.7: 5/min/IP). The production limiter — a shared
    store covering every process, plus the 10/hour/account tier — replaces
    this object behind the same ``allow`` interface."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or load_settings()

    # -- wiring: the composition root owns every infrastructure object -----
    registry = TenantRegistry(settings.control_db_url)
    router = TenantRouter(registry, settings.tenant_db_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        router.dispose()

    app = FastAPI(
        title="Guardian Lens Control Plane",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    # TRD 12.1: browser -> control plane crosses a trust boundary under a
    # CORS *allowlist*. The browser's preflight is the reason a same-machine
    # dev setup (:5173 -> :8000) fails without this — the API worked from
    # curl and the test client all along, because neither sends a preflight.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "If-None-Match"],
        expose_headers=["ETag"],
    )
    tokens = TokenService(
        settings.jwt_secret,
        access_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_ttl_seconds=settings.refresh_token_ttl_seconds,
        agent_ttl_seconds=settings.agent_token_ttl_seconds,
    )
    app.state.settings = settings
    app.state.tenant_registry = registry
    app.state.tenant_router = router
    app.state.token_service = tokens
    app.state.evidence_store = FilesystemEvidenceStore(settings.evidence_root)
    app.state.credential_sealer = build_sealer(
        settings.camera_key, settings.camera_key_id
    )
    app.state.identity_service = IdentityService(
        registry,
        router,
        tokens,
        access_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_ttl_seconds=settings.refresh_token_ttl_seconds,
        agent_ttl_seconds=settings.agent_token_ttl_seconds,
    )
    app.state.login_limiter = LoginRateLimiter(
        settings.login_rate_limit, settings.login_rate_window_seconds
    )
    # Self-service auth — CS-AU-10 (v1.4). One limiter per route so probing
    # one flow cannot starve another; same mechanism, same replacement path
    # as the login limiter.
    app.state.self_service = SelfServiceAuthService(registry, router, settings)
    app.state.signup_limiter = LoginRateLimiter(
        settings.signup_rate_limit, settings.login_rate_window_seconds
    )
    app.state.reset_request_limiter = LoginRateLimiter(
        settings.password_reset_request_rate_limit,
        settings.login_rate_window_seconds,
    )
    app.state.reset_limiter = LoginRateLimiter(
        settings.password_reset_rate_limit, settings.login_rate_window_seconds
    )
    app.state.live_preview_store = LivePreviewStore()
    app.state.ptz_command_store = PtzCommandStore()

    # -- routes -------------------------------------------------------------
    prefix = "/api/v1"
    app.include_router(health_routes.router, prefix=prefix)
    app.include_router(auth_routes.router, prefix=prefix)
    app.include_router(ingest_routes.router, prefix=prefix)
    app.include_router(live_routes.router, prefix=prefix)
    app.include_router(review_routes.router, prefix=prefix)
    app.include_router(reports_routes.router, prefix=prefix)
    app.include_router(config_routes.router, prefix=prefix)
    app.include_router(discovery_routes.router, prefix=prefix)
    app.include_router(audit_routes.router, prefix=prefix)

    # -- request tracing ----------------------------------------------------
    @app.middleware("http")
    async def trace_requests(request: Request, call_next):  # noqa: ANN001, ANN202
        trace_id_var.set(str(uuid.uuid4()))
        tenant_var.set("")
        user_id_var.set("")
        started = time.monotonic()
        response: Response = await call_next(request)
        log_event(
            _log,
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return response

    # -- error translation --------------------------------------------------
    @app.exception_handler(GuardianError)
    async def handle_guardian_error(
        request: Request, exc: GuardianError
    ) -> JSONResponse:
        if exc.http_status >= 500:
            # 5xx must stay observable server-side even though the client
            # sees only the envelope (BACKEND_CODING_RULES 16).
            log_event(
                _log,
                "http.server_error",
                level=logging.ERROR,
                error_code=exc.code,
                exception=type(exc).__name__,
            )
        return JSONResponse(
            status_code=exc.http_status,
            content=envelope(
                exc.code, exc.message, trace_id_var.get(), exc.field, exc.extra
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {"loc": (), "msg": "invalid request"}
        field = ".".join(
            str(part) for part in first["loc"] if part not in ("body", "query")
        )
        return JSONResponse(
            status_code=422,
            content=envelope(
                "GL-4220", str(first["msg"]), trace_id_var.get(), field or None
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Framework-raised 404/405 etc., re-shaped into the envelope. The
        # 404 on a route that does not exist is itself load-bearing: the
        # bypass suite asserts the bulk decision route answers exactly this.
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(
                f"GL-{exc.status_code}0", str(exc.detail), trace_id_var.get()
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            _log,
            "http.unhandled_exception",
            level=logging.ERROR,
            exception=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=envelope(
                "GL-5000", "internal server error", trace_id_var.get()
            ),
        )

    return app
