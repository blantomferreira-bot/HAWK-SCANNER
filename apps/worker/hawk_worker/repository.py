import json
from hashlib import sha256
from datetime import datetime
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hawk_worker.bootstrap import add_api_to_path
from hawk_worker.models import CatalogCoin, CatalogMarket, CoinSnapshot, MarketSnapshot

add_api_to_path()

from src.domain.scoring.hawk_score import HawkScoreResult  # noqa: E402


class ScannerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_run(self, run_id: str, started_at: datetime) -> None:
        await self.session.execute(text(
            """INSERT INTO scanner_runs (id, status, started_at, metadata)
               VALUES (:id, 'RUNNING', :started_at, CAST(:metadata AS jsonb))"""
        ), {"id": run_id, "started_at": started_at, "metadata": json.dumps({"pipeline": "public-data"})})
        await self.session.commit()

    async def finish_run(self, run_id: str, status: str, coins_seen: int, scores_saved: int, alerts_made: int, error: str | None = None) -> None:
        await self.session.execute(text(
            """UPDATE scanner_runs SET status = :status, completed_at = now(), coins_seen = :coins_seen,
               scores_saved = :scores_saved, alerts_made = :alerts_made, error = :error WHERE id = :id"""
        ), {"id": run_id, "status": status, "coins_seen": coins_seen, "scores_saved": scores_saved,
            "alerts_made": alerts_made, "error": error})
        await self.session.commit()

    async def active_coins(self) -> list[dict[str, Any]]:
        result = await self.session.execute(text(
            "SELECT id, symbol, metadata FROM coins WHERE is_active = true ORDER BY symbol"
        ))
        return [dict(row) for row in result.mappings().all()]

    async def upsert_catalog_coins(self, coins: list[CatalogCoin]) -> int:
        """Stable external-id derived keys make catalog refreshes idempotent."""
        for coin in coins:
            coin_id = f"cng_{sha256(coin.external_id.encode()).hexdigest()[:24]}"
            metadata = json.dumps({"coingecko_id": coin.external_id, "market_cap_rank": coin.market_cap_rank})
            await self.session.execute(text(
                """INSERT INTO coins (id, symbol, name, slug, asset_type, is_active, metadata, created_at, updated_at)
                   VALUES (:id, :symbol, :name, :slug, 'CRYPTOCURRENCY', true, CAST(:metadata AS jsonb), now(), now())
                   ON CONFLICT (slug) DO UPDATE SET symbol = EXCLUDED.symbol, name = EXCLUDED.name,
                       is_active = true, metadata = EXCLUDED.metadata, updated_at = now()"""
            ), {"id": coin_id, "symbol": coin.symbol, "name": coin.name, "slug": coin.external_id, "metadata": metadata})
        await self.session.commit()
        return len(coins)

    async def upsert_binance_markets(self, markets: list[CatalogMarket]) -> int:
        exchange_id = "exch_binance"
        await self.session.execute(text(
            """INSERT INTO exchanges (id, code, name, website_url, api_base_url, is_active, metadata, created_at, updated_at)
               VALUES (:id, 'BINANCE', 'Binance', 'https://www.binance.com', 'https://api.binance.com', true, '{}'::jsonb, now(), now())
               ON CONFLICT (code) DO UPDATE SET is_active = true, updated_at = now()"""
        ), {"id": exchange_id})
        result = await self.session.execute(text(
            "SELECT id, upper(symbol) AS symbol FROM coins WHERE is_active = true"
        ))
        coins_by_symbol: dict[str, str] = {}
        for row in result.mappings():
            coins_by_symbol.setdefault(row["symbol"], row["id"])
        quote_coin_id = coins_by_symbol.get("USDT")
        if quote_coin_id is None:
            await self.session.commit()
            return 0
        created = 0
        for market in markets:
            base_coin_id = coins_by_symbol.get(market.base_symbol.upper())
            if base_coin_id is None:
                continue
            market_id = f"mkt_binance_{sha256(market.symbol.encode()).hexdigest()[:24]}"
            await self.session.execute(text(
                """INSERT INTO markets (id, exchange_id, base_coin_id, quote_coin_id, symbol, market_type, is_active, metadata, created_at, updated_at)
                   VALUES (:id, :exchange_id, :base_coin_id, :quote_coin_id, :symbol, 'SPOT', true, '{}'::jsonb, now(), now())
                   ON CONFLICT (exchange_id, symbol, market_type) DO UPDATE SET base_coin_id = EXCLUDED.base_coin_id,
                       quote_coin_id = EXCLUDED.quote_coin_id, is_active = true, updated_at = now()"""
            ), {"id": market_id, "exchange_id": exchange_id, "base_coin_id": base_coin_id,
                "quote_coin_id": quote_coin_id, "symbol": market.symbol})
            created += 1
        await self.session.commit()
        return created

    async def record_source_consultation(self, source: str, status: str, detail: str | None) -> None:
        await self.session.execute(text(
            """INSERT INTO logs (level, service, event, message, context, occurred_at)
               VALUES (:level, 'scanner-worker', 'source_consultation', :message, CAST(:context AS jsonb), now())"""
        ), {"level": "INFO" if status == "AVAILABLE" else "WARNING", "message": f"{source}: {status}",
            "context": json.dumps({"source": source, "status": status, "detail": detail})})
        await self.session.commit()

    async def active_markets(self) -> list[dict[str, Any]]:
        result = await self.session.execute(text(
            """SELECT m.id, m.symbol, m.base_coin_id, e.code AS exchange_code
               FROM markets m JOIN exchanges e ON e.id = m.exchange_id
               WHERE m.is_active = true AND e.is_active = true"""
        ))
        return [dict(row) for row in result.mappings().all()]

    async def prices_before(self, observed_at: datetime) -> Mapping[str, float]:
        result = await self.session.execute(text(
            """SELECT DISTINCT ON (coin_id) coin_id, close FROM history
               WHERE market_id IS NULL AND closed_at < :observed_at
               ORDER BY coin_id, closed_at DESC"""
        ), {"observed_at": observed_at})
        return {row["coin_id"]: float(row["close"]) for row in result.mappings().all()}

    async def persist_coin_snapshots(self, snapshots: list[CoinSnapshot], observed_at: datetime) -> None:
        for snapshot in snapshots:
            values = {"id": snapshot.coin_id, "source": snapshot.source, "observed_at": observed_at}
            for metric_type, value in (("PRICE", snapshot.price), ("MARKET_CAP", snapshot.market_cap), ("VOLUME", snapshot.spot_volume)):
                if value is not None:
                    await self.session.execute(text(
                        """INSERT INTO metrics (coin_id, market_id, type, interval, value, source, observed_at, metadata, created_at)
                           VALUES (:id, NULL, :type, 'TEN_MINUTES', :value, :source, :observed_at, '{}'::jsonb, now())"""
                    ), {**values, "type": metric_type, "value": value})
            if snapshot.price is not None:
                await self.session.execute(text(
                    """INSERT INTO history (coin_id, market_id, interval, open, high, low, close, volume, quote_volume, source, opened_at, closed_at, created_at)
                       VALUES (:id, NULL, 'TEN_MINUTES', :price, :price, :price, :price, :volume, :volume,
                               :source, :observed_at, :observed_at, now())"""
                ), {**values, "price": snapshot.price, "volume": snapshot.spot_volume})
        await self.session.commit()

    async def persist_market_snapshots(self, snapshots: list[MarketSnapshot], observed_at: datetime) -> None:
        for snapshot in snapshots:
            values = {"coin_id": snapshot.coin_id, "market_id": snapshot.market_id, "source": snapshot.source, "observed_at": observed_at}
            for metric_type, value in (("PRICE", snapshot.price), ("VOLUME", snapshot.spot_volume), ("SPREAD", snapshot.spread), ("DEPTH", snapshot.bid_depth), ("DEPTH", snapshot.ask_depth)):
                if value is not None:
                    await self.session.execute(text(
                        """INSERT INTO metrics (coin_id, market_id, type, interval, value, source, observed_at, metadata, created_at)
                           VALUES (:coin_id, :market_id, :type, 'TEN_MINUTES', :value, :source, :observed_at, '{}'::jsonb, now())"""
                    ), {**values, "type": metric_type, "value": value})
            if snapshot.price is not None:
                await self.session.execute(text(
                    """INSERT INTO history (coin_id, market_id, interval, open, high, low, close, volume, quote_volume, source, opened_at, closed_at, created_at)
                       VALUES (:coin_id, :market_id, 'TEN_MINUTES', :price, :price, :price, :price, :volume, :volume,
                               :source, :observed_at, :observed_at, now())"""
                ), {**values, "price": snapshot.price, "volume": snapshot.spot_volume})
        await self.session.commit()

    async def persist_score(self, coin_id: str, result: HawkScoreResult, model_version: str, observed_at: datetime) -> str:
        score_id = f"scr_{uuid4().hex}"
        factors = json.dumps({
            "regime": result.regime, "confidence": result.confidence, "weights": result.feature_weights,
            "signals": result.normalized_signals, "contributions": result.contributions,
        })
        values = {"id": score_id, "coin_id": coin_id, "model_version": model_version, "value": result.score,
                  "confidence": result.confidence, "direction": "BULLISH" if result.score >= 50 else "BEARISH",
                  "factors": factors, "calculated_at": observed_at}
        await self.session.execute(text(
            """INSERT INTO scores (id, coin_id, market_id, model_version, value, confidence, direction, factors, calculated_at, created_at)
               VALUES (:id, :coin_id, NULL, :model_version, :value, :confidence, :direction, CAST(:factors AS jsonb), :calculated_at, now())"""
        ), values)
        await self.session.execute(text(
            """INSERT INTO score_history (coin_id, market_id, model_version, value, confidence, direction, factors, calculated_at)
               VALUES (:coin_id, NULL, :model_version, :value, :confidence, :direction, CAST(:factors AS jsonb), :calculated_at)"""
        ), values)
        await self.session.commit()
        return score_id

    async def create_alert(self, run_id: str, coin_id: str, score_id: str, score: float, threshold: float, payload: Mapping[str, Any]) -> str | None:
        alert_id = f"sal_{uuid4().hex}"
        result = await self.session.execute(text(
            """INSERT INTO scanner_alerts (id, scanner_run_id, coin_id, score_id, score_value, threshold, status, payload, created_at)
               VALUES (:id, :run_id, :coin_id, :score_id, :score, :threshold, 'PENDING', CAST(:payload AS jsonb), now())
               ON CONFLICT (coin_id, score_id) DO NOTHING RETURNING id"""
        ), {"id": alert_id, "run_id": run_id, "coin_id": coin_id, "score_id": score_id, "score": score,
            "threshold": threshold, "payload": json.dumps(dict(payload))})
        await self.session.commit()
        row = result.mappings().first()
        return row["id"] if row else None

    async def create_delivery(self, alert_id: str, channel: str, destination: str) -> str:
        delivery_id = f"sdl_{uuid4().hex}"
        result = await self.session.execute(text(
            """INSERT INTO scanner_alert_deliveries (id, scanner_alert_id, channel, destination, status, created_at)
               VALUES (:id, :alert_id, :channel, :destination, 'PENDING', now())
               ON CONFLICT (scanner_alert_id, channel, destination) DO UPDATE SET status = 'PENDING', error = NULL, attempted_at = now()
               RETURNING id"""
        ), {"id": delivery_id, "alert_id": alert_id, "channel": channel, "destination": destination})
        await self.session.commit()
        row = result.mappings().first()
        return row["id"] if row else delivery_id

    async def finish_delivery(self, delivery_id: str, delivered: bool, error: str | None = None) -> None:
        await self.session.execute(text(
            """UPDATE scanner_alert_deliveries SET status = :status, attempted_at = now(),
               delivered_at = CASE WHEN :delivered THEN now() ELSE NULL END, error = :error WHERE id = :id"""
        ), {"id": delivery_id, "status": "DELIVERED" if delivered else "FAILED", "delivered": delivered, "error": error})
        await self.session.commit()

    async def finish_alert(self, alert_id: str, delivered: bool) -> None:
        await self.session.execute(text("UPDATE scanner_alerts SET status = :status WHERE id = :id"), {
            "id": alert_id, "status": "DELIVERED" if delivered else "FAILED",
        })
        await self.session.commit()
