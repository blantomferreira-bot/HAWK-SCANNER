from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from src.config.settings import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_token(subject: str, role: str, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expiration = now + (
        timedelta(minutes=settings.jwt_access_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.jwt_refresh_ttl_days)
    )
    return jwt.encode(
        {"sub": subject, "role": role, "type": token_type, "iat": now, "exp": expiration},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, str]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from error
    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return {"id": str(payload["sub"]), "role": str(payload.get("role", "USER"))}
