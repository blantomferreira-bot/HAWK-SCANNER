import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from src.infrastructure.repositories import SqlRepository
from src.presentation.dependencies import AdminUser, DbSession
from src.presentation.schemas import CreatePlanRequest, GrantSubscriptionRequest

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("")
async def overview(_: AdminUser, session: DbSession):
    row = await SqlRepository(session).one(
        """SELECT
             (SELECT count(*) FROM users WHERE deleted_at IS NULL) AS users,
             (SELECT count(*) FROM subscriptions WHERE status = 'ACTIVE') AS active_subscriptions,
             (SELECT count(*) FROM coins WHERE is_active = true) AS active_coins,
             (SELECT count(*) FROM alerts WHERE status = 'ACTIVE') AS active_alerts,
             (SELECT max(calculated_at) FROM scores) AS latest_score_at"""
    )
    return {"data": row}


@router.get("/users")
async def users(_: AdminUser, session: DbSession, page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)):
    rows = await SqlRepository(session).many(
        """SELECT id, email, display_name, role, status, email_verified_at, last_login_at, created_at
           FROM users WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT :limit OFFSET :offset""",
        {"limit": page_size, "offset": (page - 1) * page_size},
    )
    return {"data": rows, "meta": {"page": page, "page_size": page_size}}


@router.get("/plans")
async def plans(_: AdminUser, session: DbSession):
    rows = await SqlRepository(session).many(
        """SELECT id, code, name, description, billing_interval, price_cents, currency, trial_days,
                  max_watchlists, max_alerts, max_api_keys, entitlements, is_active, created_at
           FROM plans ORDER BY price_cents, billing_interval"""
    )
    return {"data": rows}


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(payload: CreatePlanRequest, _: AdminUser, session: DbSession):
    row = await SqlRepository(session).write_one(
        """INSERT INTO plans (id, code, name, billing_interval, price_cents, currency, trial_days,
                               max_watchlists, max_alerts, max_api_keys, entitlements, is_active, created_at, updated_at)
           VALUES (:id, :code, :name, :billing_interval, :price_cents, 'USD', 0, :max_watchlists,
                   :max_alerts, :max_api_keys, CAST(:entitlements AS jsonb), true, now(), now())
           RETURNING id, code, name, billing_interval, price_cents, max_watchlists, max_alerts, max_api_keys, entitlements""",
        {"id": f"pln_{uuid4().hex}", "code": payload.code, "name": payload.name,
         "billing_interval": payload.billing_interval, "price_cents": payload.price_cents,
         "max_watchlists": payload.max_watchlists, "max_alerts": payload.max_alerts,
         "max_api_keys": payload.max_api_keys, "entitlements": json.dumps(payload.entitlements)},
    )
    return {"data": row}


@router.get("/subscriptions")
async def subscriptions(_: AdminUser, session: DbSession, page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)):
    rows = await SqlRepository(session).many(
        """SELECT s.id, s.user_id, u.email, s.plan_id, p.code AS plan_code, s.status, s.current_period_start,
                  s.current_period_end, s.cancel_at_period_end, s.created_at
           FROM subscriptions s JOIN users u ON u.id = s.user_id JOIN plans p ON p.id = s.plan_id
           ORDER BY s.created_at DESC LIMIT :limit OFFSET :offset""",
        {"limit": page_size, "offset": (page - 1) * page_size},
    )
    return {"data": rows, "meta": {"page": page, "page_size": page_size}}


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def grant_subscription(payload: GrantSubscriptionRequest, _: AdminUser, session: DbSession):
    repository = SqlRepository(session)
    user = await repository.one("SELECT id FROM users WHERE id = :id AND deleted_at IS NULL", {"id": payload.user_id})
    plan = await repository.one("SELECT id FROM plans WHERE id = :id AND is_active = true", {"id": payload.plan_id})
    if user is None or plan is None:
        raise HTTPException(status_code=404, detail="User or active plan not found")
    row = await repository.write_one(
        """INSERT INTO subscriptions (id, user_id, plan_id, status, current_period_start, current_period_end,
                                       cancel_at_period_end, created_at, updated_at)
           VALUES (:id, :user_id, :plan_id, :status, :start_at, :end_at, false, now(), now())
           RETURNING id, user_id, plan_id, status, current_period_start, current_period_end""",
        {"id": f"sub_{uuid4().hex}", "user_id": payload.user_id, "plan_id": payload.plan_id,
         "status": payload.status, "start_at": payload.current_period_start, "end_at": payload.current_period_end},
    )
    return {"data": row}
