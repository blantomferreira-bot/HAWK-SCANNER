from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.security import decode_access_token
from src.infrastructure.database import get_db_session
from src.infrastructure.repositories import SqlRepository

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def current_user(
    session: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    identity = decode_access_token(credentials.credentials)
    user = await SqlRepository(session).one(
        """SELECT id, email, role, status FROM users
           WHERE id = :id AND status = 'ACTIVE' AND deleted_at IS NULL""",
        {"id": identity["id"]},
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable")
    return user


async def admin_user(user: Annotated[dict[str, str], Depends(current_user)]) -> dict[str, str]:
    if user["role"] not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return user


CurrentUser = Annotated[dict[str, str], Depends(current_user)]
AdminUser = Annotated[dict[str, str], Depends(admin_user)]
