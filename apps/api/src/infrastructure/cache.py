import json
from typing import Any

import redis.asyncio as redis
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class RedisCache:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(get_settings().redis_url, encoding="utf-8", decode_responses=True)
        return self._client

    async def get_json(self, key: str) -> Any | None:
        try:
            value = await (await self.client()).get(key)
            return json.loads(value) if value else None
        except Exception as error:  # Cache failure must not make read APIs unavailable.
            logger.warning("cache_read_failed", key=key, error=str(error))
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            await (await self.client()).set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception as error:
            logger.warning("cache_write_failed", key=key, error=str(error))

    async def increment(self, key: str, ttl_seconds: int) -> int | None:
        try:
            client = await self.client()
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, ttl_seconds, nx=True)
                result = await pipe.execute()
            return int(result[0])
        except Exception as error:
            logger.warning("rate_limit_store_failed", key=key, error=str(error))
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


cache = RedisCache()
