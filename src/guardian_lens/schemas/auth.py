"""Authentication schemas — TRD 10.2, CS-AU-10 (v1.4)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

#: Plain str, not EmailStr: EmailStr requires the email-validator package,
#: and the only consumer of the address is a hash lookup plus a CITEXT
#: equality — malformed addresses simply fail to match.
EmailField = Annotated[str, Field(min_length=3, max_length=320)]

#: The password policy, shared by sign-up and reset so the two flows cannot
#: drift apart: minimum 12, maximum 128, NO composition rules (CS-AU-15,
#: NIST 800-63B). A violation is an ordinary 422 field error — password
#: quality is about the caller's own submission and is not
#: enumeration-sensitive.
NewPasswordField = Annotated[str, Field(min_length=12, max_length=128)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailField
    password: str = Field(min_length=1, max_length=1024)


class UserInfo(BaseModel):
    id: UUID
    full_name: str
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class AgentLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # "slug:agent_id:secret" — the slug routes, the secret proves.
    credential: str = Field(min_length=1, max_length=1024)


class AgentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    email: EmailField
    password: NewPasswordField
    # The site code IS the tenant slug — routing only, exactly like the
    # slug inside an agent credential: it selects which tenant the sign-up
    # is addressed to, and whether it exists is never disclosed (CS-AU-16).
    site_code: str = Field(min_length=1, max_length=64)


class SignupAccepted(BaseModel):
    """The ONE sign-up response. Created, duplicate, unknown site and
    sign-up-disabled all serialise to this exact body (CS-AU-16)."""

    status: str = "accepted"
    message: str = "Account requested. A site administrator assigns access."


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailField


class ResetRequestAccepted(BaseModel):
    """The ONE reset-request response, known and unknown address alike
    (CS-AU-17)."""

    status: str = "accepted"


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The token alone names no tenant; the email routes, the way login
    # routes. The reset URL carries both (?email=&token=).
    email: EmailField
    token: str = Field(min_length=1, max_length=512)
    new_password: NewPasswordField


class ResetCompleted(BaseModel):
    status: str = "ok"
