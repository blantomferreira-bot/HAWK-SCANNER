import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from src.infrastructure.repositories import SqlRepository
from src.presentation.dependencies import CurrentUser, DbSession
from src.presentation.schemas import AddWatchlistCoinRequest, AlertCreateRequest, AlertUpdateRequest, CreateWatchlistRequest

router = APIRouter(tags=["Watchlists and alerts"])

VALID_ALERT_TYPES = {"SCORE_THRESHOLD", "SCORE_CHANGE", "PRICE_CHANGE", "VOLUME_SPIKE", "FUNDING_EXTREME", "OPEN_INTEREST_CHANGE", "LIQUIDATION_SPIKE", "WHALE_TRANSFER"}
VALID_ALERT_CHANNELS = {"IN_APP", "EMAIL", "TELEGRAM", "DISCORD", "WEBHOOK"}
VALID_ALERT_STATUSES = {"ACTIVE", "PAUSED", "ARCHIVED"}


@router.get("/subscription", tags=["Subscriptions"])
async def current_subscription(user: CurrentUser, session: DbSession):
    row = await SqlRepository(session).one(
        """SELECT s.id, s.status, s.current_period_start, s.current_period_end, s.cancel_at_period_end,
                  s.provider_customer_id, s.provider_subscription_id, p.code AS plan_code, p.name AS plan_name,
                  p.entitlements
           FROM subscriptions s JOIN plans p ON p.id = s.plan_id
           WHERE s.user_id = :user_id
           ORDER BY s.current_period_end DESC, s.created_at DESC
           LIMIT 1""",
        {"user_id": user["id"]},
    )
    return {"data": row, "meta": {}}


@router.get("/watchlist")
async def list_watchlists(user: CurrentUser, session: DbSession):
    rows = await SqlRepository(session).many(
        """SELECT w.id, w.name, w.description, w.is_default, w.created_at, w.updated_at,
                  COALESCE(json_agg(json_build_object('id', i.id, 'coin_id', i.coin_id, 'symbol', c.symbol,
                    'name', c.name, 'note', i.note) ORDER BY c.symbol) FILTER (WHERE i.id IS NOT NULL), '[]') AS items
           FROM watchlists w LEFT JOIN watchlist_items i ON i.watchlist_id = w.id
           LEFT JOIN coins c ON c.id = i.coin_id WHERE w.user_id = :user_id
           GROUP BY w.id ORDER BY w.is_default DESC, w.name""",
        {"user_id": user["id"]},
    )
    return {"data": rows, "meta": {}}


@router.post("/watchlist", status_code=status.HTTP_201_CREATED)
async def create_watchlist(payload: CreateWatchlistRequest, user: CurrentUser, session: DbSession):
    try:
        row = await SqlRepository(session).write_one(
            """INSERT INTO watchlists (id, user_id, name, description, is_default, created_at, updated_at)
               VALUES (:id, :user_id, :name, :description,
                       NOT EXISTS (SELECT 1 FROM watchlists WHERE user_id = :user_id), now(), now())
               RETURNING id, name, description, is_default, created_at""",
            {"id": f"wls_{uuid4().hex}", "user_id": user["id"], "name": payload.name, "description": payload.description},
        )
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A watchlist with this name already exists") from error
    return {"data": row}


@router.post("/watchlist/{watchlist_id}/coins", status_code=status.HTTP_201_CREATED)
async def add_watchlist_coin(watchlist_id: str, payload: AddWatchlistCoinRequest, user: CurrentUser, session: DbSession):
    repository = SqlRepository(session)
    owned = await repository.one("SELECT id FROM watchlists WHERE id = :id AND user_id = :user_id", {"id": watchlist_id, "user_id": user["id"]})
    if owned is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    coin = await repository.one("SELECT id FROM coins WHERE id = :id", {"id": payload.coin_id})
    if coin is None:
        raise HTTPException(status_code=404, detail="Coin not found")
    row = await repository.write_one(
        """INSERT INTO watchlist_items (id, watchlist_id, coin_id, note, created_at)
           VALUES (:id, :watchlist_id, :coin_id, :note, now())
           ON CONFLICT (watchlist_id, coin_id) DO UPDATE SET note = EXCLUDED.note
           RETURNING id, watchlist_id, coin_id, note, created_at""",
        {"id": f"wli_{uuid4().hex}", "watchlist_id": watchlist_id, "coin_id": payload.coin_id, "note": payload.note},
    )
    return {"data": row}


@router.delete("/watchlist/{watchlist_id}/coins/{coin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_coin(watchlist_id: str, coin_id: str, user: CurrentUser, session: DbSession):
    row = await SqlRepository(session).write_one(
        """DELETE FROM watchlist_items i USING watchlists w
           WHERE i.watchlist_id = w.id AND i.watchlist_id = :watchlist_id AND i.coin_id = :coin_id
             AND w.user_id = :user_id RETURNING i.id""",
        {"watchlist_id": watchlist_id, "coin_id": coin_id, "user_id": user["id"]},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")


@router.get("/alerts")
async def list_alerts(user: CurrentUser, session: DbSession, status_filter: str | None = Query(default=None, alias="status")):
    rows = await SqlRepository(session).many(
        """SELECT id, coin_id, type, channel, status, name, conditions, cooldown_secs, last_triggered_at, created_at, updated_at
           FROM alerts WHERE user_id = :user_id AND (:status IS NULL OR status::text = :status) ORDER BY created_at DESC""",
        {"user_id": user["id"], "status": status_filter},
    )
    return {"data": rows, "meta": {}}


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
async def create_alert(payload: AlertCreateRequest, user: CurrentUser, session: DbSession):
    if payload.type not in VALID_ALERT_TYPES or payload.channel not in VALID_ALERT_CHANNELS:
        raise HTTPException(status_code=422, detail="Unsupported alert type or channel")
    repository = SqlRepository(session)
    if payload.coin_id and await repository.one("SELECT id FROM coins WHERE id = :id", {"id": payload.coin_id}) is None:
        raise HTTPException(status_code=404, detail="Coin not found")
    row = await repository.write_one(
        """INSERT INTO alerts (id, user_id, coin_id, type, channel, status, name, conditions, destination, cooldown_secs, created_at, updated_at)
           VALUES (:id, :user_id, :coin_id, :type, :channel, 'ACTIVE', :name, CAST(:conditions AS jsonb), :destination, :cooldown_secs, now(), now())
           RETURNING id, coin_id, type, channel, status, name, conditions, cooldown_secs, created_at""",
        {"id": f"alr_{uuid4().hex}", "user_id": user["id"], "coin_id": payload.coin_id, "type": payload.type, "channel": payload.channel,
         "name": payload.name, "conditions": json.dumps(payload.conditions), "destination": payload.destination, "cooldown_secs": payload.cooldown_secs},
    )
    return {"data": row}


@router.patch("/alerts/{alert_id}")
async def update_alert(alert_id: str, payload: AlertUpdateRequest, user: CurrentUser, session: DbSession):
    if payload.status is not None and payload.status not in VALID_ALERT_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported alert status")
    row = await SqlRepository(session).write_one(
        """UPDATE alerts SET name = COALESCE(:name, name), status = COALESCE(:status, status),
               conditions = COALESCE(CAST(:conditions AS jsonb), conditions), destination = COALESCE(:destination, destination),
               cooldown_secs = COALESCE(:cooldown_secs, cooldown_secs), updated_at = now()
           WHERE id = :id AND user_id = :user_id
           RETURNING id, coin_id, type, channel, status, name, conditions, cooldown_secs, updated_at""",
        {"id": alert_id, "user_id": user["id"], "name": payload.name, "status": payload.status,
         "conditions": json.dumps(payload.conditions) if payload.conditions is not None else None,
         "destination": payload.destination, "cooldown_secs": payload.cooldown_secs},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": row}


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: str, user: CurrentUser, session: DbSession):
    row = await SqlRepository(session).write_one("DELETE FROM alerts WHERE id = :id AND user_id = :user_id RETURNING id", {"id": alert_id, "user_id": user["id"]})
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
