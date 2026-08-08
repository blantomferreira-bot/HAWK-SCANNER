from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TokenResponse(ApiModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CreateWatchlistRequest(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class AddWatchlistCoinRequest(ApiModel):
    coin_id: str
    note: str | None = Field(default=None, max_length=500)


class AlertCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    channel: str
    conditions: dict[str, Any]
    coin_id: str | None = None
    destination: str | None = Field(default=None, max_length=2048)
    cooldown_secs: int = Field(default=900, ge=60, le=86400)


class AlertUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = None
    conditions: dict[str, Any] | None = None
    destination: str | None = Field(default=None, max_length=2048)
    cooldown_secs: int | None = Field(default=None, ge=60, le=86400)


class CreatePlanRequest(ApiModel):
    code: str = Field(pattern=r"^[a-z0-9_-]{2,32}$")
    name: str = Field(min_length=2, max_length=80)
    billing_interval: str
    price_cents: int = Field(ge=0)
    max_watchlists: int = Field(default=1, ge=0)
    max_alerts: int = Field(default=3, ge=0)
    max_api_keys: int = Field(default=0, ge=0)
    entitlements: dict[str, Any] = Field(default_factory=dict)


class Page(ApiModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    cached: bool = False
