"""Authentication routes — TRD 10.2, MOD-12; self-service per CS-AU-10 (v1.4)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from guardian_lens.core.errors import RateLimitedError
from guardian_lens.schemas.auth import (
    AgentLoginRequest,
    AgentTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetCompleted,
    ResetPasswordRequest,
    ResetRequestAccepted,
    SignupAccepted,
    SignupRequest,
    TokenResponse,
    UserInfo,
)
from guardian_lens.services.identity import IdentityService
from guardian_lens.services.self_service import SelfServiceAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _identity(request: Request) -> IdentityService:
    return request.app.state.identity_service


def _self_service(request: Request) -> SelfServiceAuthService:
    return request.app.state.self_service


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    # TRD 12.7: 5/min/IP. The in-memory window suffices for a single
    # process at MVP; the production limiter (shared store, plus the
    # 10/hour/account tier) replaces app.state.login_limiter when the
    # deployment grows past one process.
    if not request.app.state.login_limiter.allow(_client_ip(request)):
        raise RateLimitedError("too many login attempts; try again shortly")

    pair = _identity(request).login(body.email, body.password)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=UserInfo(id=pair.user_id, full_name=pair.full_name, roles=pair.roles),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    pair = _identity(request).refresh(body.refresh_token)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=UserInfo(id=pair.user_id, full_name=pair.full_name, roles=pair.roles),
    )


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, request: Request) -> Response:
    _identity(request).logout(body.refresh_token)
    return Response(status_code=204)


@router.post("/agent", response_model=AgentTokenResponse)
def agent_login(body: AgentLoginRequest, request: Request) -> AgentTokenResponse:
    token = _identity(request).agent_login(body.credential)
    return AgentTokenResponse(
        access_token=token.access_token, expires_in=token.expires_in
    )


# -- self-service — CS-AU-10 (v1.4) -------------------------------------------


@router.post("/signup", response_model=SignupAccepted, status_code=202)
def sign_up(body: SignupRequest, request: Request) -> SignupAccepted:
    # 3/min/IP through the same limiter mechanism as login (TRD 12.7
    # posture; the shared-store production limiter replaces the object,
    # not this call site).
    if not request.app.state.signup_limiter.allow(_client_ip(request)):
        raise RateLimitedError("too many sign-up attempts; try again shortly")

    _self_service(request).sign_up(
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        site_code=body.site_code,
    )
    # ALWAYS this body, created or not: the service returns nothing the
    # response could vary with (CS-AU-16).
    return SignupAccepted()


@router.post(
    "/password-reset-request", response_model=ResetRequestAccepted, status_code=202
)
def request_password_reset(
    body: ForgotPasswordRequest, request: Request
) -> ResetRequestAccepted:
    if not request.app.state.reset_request_limiter.allow(_client_ip(request)):
        raise RateLimitedError("too many reset requests; try again shortly")

    _self_service(request).request_password_reset(body.email)
    # ALWAYS this body, known address or not (CS-AU-17).
    return ResetRequestAccepted()


@router.post("/password-reset", response_model=ResetCompleted)
def reset_password(body: ResetPasswordRequest, request: Request) -> ResetCompleted:
    if not request.app.state.reset_limiter.allow(_client_ip(request)):
        raise RateLimitedError("too many reset attempts; try again shortly")

    _self_service(request).reset_password(
        email=body.email, token=body.token, new_password=body.new_password
    )
    return ResetCompleted()
