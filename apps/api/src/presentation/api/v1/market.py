from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from src.infrastructure.repositories import SqlRepository
from src.presentation.cache_response import cached_payload
from src.presentation.dependencies import DbSession

router = APIRouter(tags=["Market data"])


@router.get("/coins")
async def list_coins(
    session: DbSession,
    search: str | None = Query(default=None, max_length=80),
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    key = f"coins:{search or ''}:{active_only}:{page}:{page_size}"

    async def load():
        offset = (page - 1) * page_size
        rows = await SqlRepository(session).many(
            """WITH latest_market_caps AS (
                 SELECT DISTINCT ON (coin_id) coin_id, value AS market_cap
                 FROM metrics
                 WHERE type = 'MARKET_CAP'
                 ORDER BY coin_id, observed_at DESC
               )
               SELECT c.id, c.symbol, c.name, c.slug, c.asset_type, c.contract_address, c.network,
                      c.decimals, c.is_active, c.metadata, lmc.market_cap
               FROM coins c
               LEFT JOIN latest_market_caps lmc ON lmc.coin_id = c.id
               WHERE (CAST(:search AS text) IS NULL OR symbol ILIKE :pattern OR name ILIKE :pattern)
                 AND (:active_only = false OR is_active = true)
               ORDER BY lmc.market_cap DESC NULLS LAST, c.symbol ASC
               LIMIT :limit OFFSET :offset""",
            {"search": search, "pattern": f"%{search}%" if search else None, "active_only": active_only,
             "limit": page_size, "offset": offset},
        )
        return {"data": rows, "meta": {"page": page, "page_size": page_size}}

    return await cached_payload(key, 60, load)


@router.get("/coin/{coin_id}")
async def get_coin(coin_id: str, session: DbSession):
    key = f"coin:{coin_id}"

    async def load():
        row = await SqlRepository(session).one(
            """SELECT id, symbol, name, slug, asset_type, contract_address, network, decimals, is_active, metadata
               FROM coins WHERE id = :coin_id""",
            {"coin_id": coin_id},
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Coin not found")
        return {"data": row, "meta": {}}

    return await cached_payload(key, 60, load)


@router.get("/ranking")
async def ranking(
    session: DbSession,
    model_version: str | None = None,
    direction: str | None = Query(default=None, pattern="^(BULLISH|BEARISH|NEUTRAL)$"),
    limit: int = Query(default=50, ge=1, le=100),
):
    key = f"ranking:{model_version or 'latest'}:{direction or 'all'}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """WITH latest_scores AS (
                 SELECT DISTINCT ON (s.coin_id, COALESCE(s.market_id, ''))
                        s.id, s.coin_id, s.market_id, s.model_version, s.value, s.confidence, s.direction,
                        s.factors, s.calculated_at, c.symbol, c.name
                 FROM scores s
                 JOIN coins c ON c.id = s.coin_id
                 WHERE (CAST(:model_version AS text) IS NULL OR s.model_version = CAST(:model_version AS text))
                   AND (CAST(:direction AS text) IS NULL OR s.direction::text = CAST(:direction AS text))
                 ORDER BY s.coin_id, COALESCE(s.market_id, ''), s.calculated_at DESC
               ), latest_price AS (
                 SELECT DISTINCT ON (coin_id) coin_id, value AS price
                 FROM metrics WHERE type = 'PRICE' AND market_id IS NULL
                 ORDER BY coin_id, observed_at DESC
               ), latest_volume AS (
                 SELECT DISTINCT ON (coin_id) coin_id, value AS volume
                 FROM metrics WHERE type = 'VOLUME' AND market_id IS NULL
                 ORDER BY coin_id, observed_at DESC
               )
               SELECT ls.*, lp.price, lv.volume
               FROM latest_scores ls
               LEFT JOIN latest_price lp ON lp.coin_id = ls.coin_id
               LEFT JOIN latest_volume lv ON lv.coin_id = ls.coin_id
               ORDER BY value DESC, confidence DESC, calculated_at DESC
               LIMIT :limit""",
            {"model_version": model_version, "direction": direction, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 30, load)


@router.get("/similarity")
async def similarity(
    session: DbSession,
    coin_id: str | None = None,
    model_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    """Latest ML similarity ranking from completed daily learning runs."""
    key = f"similarity:{coin_id or 'all'}:{model_type or 'latest'}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """WITH latest_training AS (
                 SELECT DISTINCT ON (model_type) id, model_type, label_definition, trained_at
                 FROM ml_training_runs
                 WHERE status = 'COMPLETED'
                   AND (CAST(:model_type AS text) IS NULL OR model_type = CAST(:model_type AS text))
                 ORDER BY model_type, trained_at DESC NULLS LAST, created_at DESC
               )
               SELECT ms.id, ms.coin_id, c.symbol, c.name, ms.score, ms.model_probability,
                      ms.leaf_agreement, ms.calculated_at, lt.model_type, lt.label_definition, lt.trained_at
               FROM ml_similarity_scores ms
               JOIN latest_training lt ON lt.id = ms.training_run_id
               JOIN coins c ON c.id = ms.coin_id
               WHERE (CAST(:coin_id AS text) IS NULL OR ms.coin_id = CAST(:coin_id AS text))
               ORDER BY ms.score DESC, ms.calculated_at DESC
               LIMIT :limit""",
            {"coin_id": coin_id, "model_type": model_type, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 300, load)


@router.get("/metrics")
async def metrics(
    session: DbSession,
    coin_id: str | None = None,
    market_id: str | None = None,
    metric_type: str | None = Query(default=None, alias="type"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    key = f"metrics:{coin_id}:{market_id}:{metric_type}:{start_at}:{end_at}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """SELECT id, coin_id, market_id, type, interval, value, source, observed_at, metadata
               FROM metrics
               WHERE (CAST(:coin_id AS text) IS NULL OR coin_id = CAST(:coin_id AS text))
                 AND (CAST(:market_id AS text) IS NULL OR market_id = CAST(:market_id AS text))
                 AND (CAST(:metric_type AS text) IS NULL OR type::text = CAST(:metric_type AS text))
                 AND (CAST(:start_at AS timestamptz) IS NULL OR observed_at >= CAST(:start_at AS timestamptz))
                 AND (CAST(:end_at AS timestamptz) IS NULL OR observed_at <= CAST(:end_at AS timestamptz))
               ORDER BY observed_at DESC LIMIT :limit""",
            {"coin_id": coin_id, "market_id": market_id, "metric_type": metric_type,
             "start_at": start_at, "end_at": end_at, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 15, load)


@router.get("/funding")
async def funding(session: DbSession, market_id: str | None = None, limit: int = Query(default=200, ge=1, le=1000)):
    key = f"funding:{market_id}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """SELECT f.id, f.market_id, m.symbol, f.rate, f.mark_price, f.next_funding_at, f.source, f.observed_at
               FROM funding f JOIN markets m ON m.id = f.market_id
               WHERE (CAST(:market_id AS text) IS NULL OR f.market_id = CAST(:market_id AS text))
               ORDER BY f.observed_at DESC LIMIT :limit""",
            {"market_id": market_id, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 15, load)


@router.get("/openinterest")
async def open_interest(session: DbSession, market_id: str | None = None, limit: int = Query(default=200, ge=1, le=1000)):
    key = f"open-interest:{market_id}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """SELECT oi.id, oi.market_id, m.symbol, oi.value, oi.value_usd, oi.source, oi.observed_at
               FROM open_interest oi JOIN markets m ON m.id = oi.market_id
               WHERE (CAST(:market_id AS text) IS NULL OR oi.market_id = CAST(:market_id AS text))
               ORDER BY oi.observed_at DESC LIMIT :limit""",
            {"market_id": market_id, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 15, load)


@router.get("/liquidations")
async def liquidations(
    session: DbSession, market_id: str | None = None, exchange_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    key = f"liquidations:{market_id}:{exchange_id}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """SELECT id, market_id, exchange_id, side, price, quantity, value_usd, source, liquidated_at, metadata
               FROM liquidations
               WHERE (CAST(:market_id AS text) IS NULL OR market_id = CAST(:market_id AS text))
                 AND (CAST(:exchange_id AS text) IS NULL OR exchange_id = CAST(:exchange_id AS text))
               ORDER BY liquidated_at DESC LIMIT :limit""",
            {"market_id": market_id, "exchange_id": exchange_id, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 15, load)


@router.get("/holders")
async def holders(session: DbSession, coin_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    key = f"holders:{coin_id}:{limit}"

    async def load():
        rows = await SqlRepository(session).many(
            """SELECT w.id, w.address, w.network, w.coin_id, w.label, w.entity_name, w.is_exchange,
                      wh.classification, wh.confidence, wh.estimated_value_usd, wh.tags
               FROM wallets w LEFT JOIN whales wh ON wh.wallet_id = w.id
               WHERE (CAST(:coin_id AS text) IS NULL OR w.coin_id = CAST(:coin_id AS text))
               ORDER BY wh.estimated_value_usd DESC NULLS LAST, w.last_seen_at DESC NULLS LAST
               LIMIT :limit""",
            {"coin_id": coin_id, "limit": limit},
        )
        return {"data": rows, "meta": {"limit": limit}}

    return await cached_payload(key, 60, load)


@router.get("/score")
async def score(session: DbSession, coin_id: str, model_version: str | None = None):
    key = f"score:{coin_id}:{model_version or 'latest'}"

    async def load():
        row = await SqlRepository(session).one(
            """SELECT id, coin_id, market_id, model_version, value, confidence, direction, factors, calculated_at, expires_at
               FROM scores WHERE coin_id = :coin_id
                 AND (CAST(:model_version AS text) IS NULL OR model_version = CAST(:model_version AS text))
               ORDER BY calculated_at DESC LIMIT 1""",
            {"coin_id": coin_id, "model_version": model_version},
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Score not found")
        return {"data": row, "meta": {}}

    return await cached_payload(key, 30, load)
