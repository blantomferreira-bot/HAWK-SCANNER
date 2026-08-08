from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlRepository:
    """Small data-access boundary; Prisma owns migrations, FastAPI consumes that schema."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def one(self, statement: str, values: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
        result = await self.session.execute(text(statement), values or {})
        row = result.mappings().first()
        return dict(row) if row else None

    async def many(self, statement: str, values: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        result = await self.session.execute(text(statement), values or {})
        return [dict(row) for row in result.mappings().all()]

    async def write_one(self, statement: str, values: Mapping[str, Any]) -> dict[str, Any] | None:
        result = await self.session.execute(text(statement), values)
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
