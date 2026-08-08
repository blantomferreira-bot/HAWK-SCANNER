from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from src.infrastructure.cache import cache


async def cached_payload(
    key: str, ttl_seconds: int, loader: Callable[[], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    hit = await cache.get_json(key)
    if hit is not None:
        hit.setdefault("meta", {})["cached"] = True
        return hit
    payload = jsonable_encoder(await loader())
    payload.setdefault("meta", {})["cached"] = False
    await cache.set_json(key, payload, ttl_seconds)
    return payload
