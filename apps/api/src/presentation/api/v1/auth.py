from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError

from src.application.security import create_token, hash_password, verify_password
from src.config.settings import get_settings
from src.infrastructure.repositories import SqlRepository
from src.presentation.dependencies import CurrentUser, DbSession, bearer_scheme
from src.presentation.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def issue_tokens(user: dict[str, str]) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user["id"], user["role"], "access"),
        refresh_token=create_token(user["id"], user["role"], "refresh"),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> TokenResponse:
    repository = SqlRepository(session)
    email = str(payload.email).lower()
    settings = get_settings()
    is_bootstrap_admin = bool(settings.bootstrap_admin_email and email == settings.bootstrap_admin_email.lower())
    try:
        user = await repository.write_one(
            """INSERT INTO users (id, email, password_hash, display_name, role, status, timezone, created_at, updated_at)
               VALUES (:id, :email, :password_hash, :display_name, :role, 'ACTIVE', 'UTC', now(), now())
               RETURNING id, email, role""",
            {"id": f"usr_{uuid4().hex}", "email": email, "role": "SUPER_ADMIN" if is_bootstrap_admin else "USER",
             "password_hash": hash_password(payload.password), "display_name": payload.display_name},
        )
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from error
    if user is None:
        raise HTTPException(status_code=500, detail="Could not create user")
    return issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    repository = SqlRepository(session)
    user = await repository.one(
        """SELECT id, email, password_hash, role FROM users
           WHERE email = :email AND status = 'ACTIVE' AND deleted_at IS NULL""",
        {"email": str(payload.email).lower()},
    )
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    await repository.write_one("UPDATE users SET last_login_at = now() WHERE id = :id RETURNING id", {"id": user["id"]})
    return issue_tokens(user)


@router.get("/me")
async def me(user: CurrentUser) -> dict[str, dict[str, str]]:
    return {"data": user}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)], session: DbSession
) -> TokenResponse:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from error
    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await SqlRepository(session).one(
        "SELECT id, email, role FROM users WHERE id = :id AND status = 'ACTIVE' AND deleted_at IS NULL",
        {"id": payload["sub"]},
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User is unavailable")
    return issue_tokens(user)
