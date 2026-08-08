from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.application.security import create_token, hash_password, verify_password
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
    try:
        user = await repository.write_one(
            """INSERT INTO users (id, email, password_hash, display_name, role, status, timezone, created_at, updated_at)
               VALUES (concat('usr_', replace(gen_random_uuid()::text, '-', '')), :email, :password_hash,
                       :display_name, 'USER', 'ACTIVE', 'UTC', now(), now())
               RETURNING id, email, role""",
            {
                "email": str(payload.email).lower(),
                "password_hash": hash_password(payload.password),
                "display_name": payload.display_name,
            },
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
    credentials: Annotated[object, Depends(bearer_scheme)], session: DbSession
) -> TokenResponse:
    # Refresh tokens are verified in the same security module, with an explicit token type check.
    from src.application.security import decode_access_token  # Deliberately avoids duplicate JWT parsing logic.

    if credentials is None or not hasattr(credentials, "credentials"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
    # decode_access_token rejects non-access tokens; refresh validation is performed below.
    import jwt
    from src.config.settings import get_settings

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
