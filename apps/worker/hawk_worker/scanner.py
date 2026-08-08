import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from hawk_worker.bootstrap import add_api_to_path

add_api_to_path()

from src.domain.scoring.hawk_score import HawkScoreEngine, RawMarketState  # noqa: E402
from src.infrastructure.cache import cache  # noqa: E402
from src.infrastructure.database import SessionLocal  # noqa: E402

from hawk_worker.calibration import DynamicCalibrator
from hawk_worker.config import ScannerSettings
from hawk_worker.models import CoinSnapshot, MarketSnapshot, NotificationMessage
from hawk_worker.mandatory_sources import MandatorySourceRegistry
from hawk_worker.notifications import NotificationService
from hawk_worker.providers import BinancePublicProvider, CoinGeckoPublicProvider
from hawk_worker.repository import ScannerRepository


class ScannerService:
    def __init__(self, settings: ScannerSettings) -> None:
        self.settings = settings
        self.score_engine = HawkScoreEngine()
        self.calibrator = DynamicCalibrator()
        self.notifier = NotificationService(settings)
        self.coin_gecko = CoinGeckoPublicProvider(settings.source_api_keys["coingecko"])
        self.binance = BinancePublicProvider()
        self.mandatory_sources = MandatorySourceRegistry(settings)

    async def run_once(self) -> dict[str, int | str]:
        run_id = f"run_{uuid4().hex}"
        started_at = datetime.now(UTC)
        lock_client = await cache.client()
        locked = await lock_client.set("hawk-scanner:scan-lock", run_id, nx=True, ex=600)
        if not locked:
            return {"run_id": run_id, "status": "SKIPPED", "reason": "scan already running"}
        coins_seen = scores_saved = alerts_made = 0
        try:
            async with SessionLocal() as session:
                repository = ScannerRepository(session)
                await repository.start_run(run_id, started_at)
                consultations = await self.mandatory_sources.consult_all()
                for consultation in consultations:
                    await repository.record_source_consultation(consultation.source, consultation.status, consultation.detail)
                if self.settings.require_all_data_sources:
                    failures = [item.source for item in consultations if item.status != "AVAILABLE"]
                    if failures:
                        raise RuntimeError(f"Mandatory data sources unavailable: {', '.join(failures)}")
                await self._refresh_catalog(repository, lock_client)
                coins, markets = await repository.active_coins(), await repository.active_markets()
                coins_seen = len(coins)
                previous_prices = await repository.prices_before(started_at)
                coin_snapshots, market_snapshots = await asyncio.gather(self.coin_gecko.fetch(coins), self.binance.fetch(markets))
                await repository.persist_coin_snapshots(coin_snapshots, started_at)
                await repository.persist_market_snapshots(market_snapshots, started_at)
                states, current_prices = self._states(coin_snapshots, market_snapshots)
                realized_returns = {
                    coin_id: current_prices[coin_id] / previous_prices[coin_id] - 1
                    for coin_id in current_prices if coin_id in previous_prices and previous_prices[coin_id] > 0
                }
                calibration = self.calibrator.calibrate(states, realized_returns, started_at.isoformat())
                scored: list[tuple[str, str, float, float]] = []
                for coin_id, state in states.items():
                    try:
                        result = self.score_engine.calculate(state, calibration)
                    except ValueError:
                        continue  # Warm-up: evidence is intentionally unavailable until data exists.
                    score_id = await repository.persist_score(coin_id, result, self.settings.model_version, started_at)
                    scores_saved += 1
                    scored.append((coin_id, score_id, result.score, result.confidence))
                scored.sort(key=lambda item: item[2], reverse=True)
                symbols = {coin["id"]: coin["symbol"] for coin in coins}
                for position, (coin_id, score_id, score, confidence) in enumerate(scored, start=1):
                    if score <= self.settings.alert_threshold:
                        continue
                    alert_id = await repository.create_alert(
                        run_id, coin_id, score_id, score, self.settings.alert_threshold,
                        {"symbol": symbols.get(coin_id, coin_id), "confidence": confidence, "ranking_position": position},
                    )
                    if alert_id is None:
                        continue
                    alerts_made += 1
                    message = NotificationMessage(coin_id, symbols.get(coin_id, coin_id), score, self.settings.alert_threshold, confidence, position)
                    delivered = await self._deliver(repository, alert_id, message)
                    await repository.finish_alert(alert_id, delivered)
                await repository.finish_run(run_id, "COMPLETED", coins_seen, scores_saved, alerts_made)
            return {"run_id": run_id, "status": "COMPLETED", "coins_seen": coins_seen, "scores_saved": scores_saved, "alerts_made": alerts_made}
        except Exception as error:
            async with SessionLocal() as session:
                await ScannerRepository(session).finish_run(run_id, "FAILED", coins_seen, scores_saved, alerts_made, str(error))
            raise
        finally:
            await lock_client.delete("hawk-scanner:scan-lock")

    async def _refresh_catalog(self, repository: ScannerRepository, lock_client) -> None:
        """Initialize and then refresh the tradable universe daily, not every scan."""
        catalog_key = "hawk-scanner:catalog:v1"
        if await lock_client.get(catalog_key):
            return
        catalog_coins = await self.coin_gecko.catalog(self.settings.coingecko_catalog_pages)
        await repository.upsert_catalog_coins(catalog_coins)
        binance_markets = await self.binance.catalog()
        await repository.upsert_binance_markets(binance_markets)
        await lock_client.set(catalog_key, "ready", ex=self.settings.catalog_refresh_seconds)

    @staticmethod
    def _states(coin_snapshots: list[CoinSnapshot], market_snapshots: list[MarketSnapshot]) -> tuple[dict[str, RawMarketState], dict[str, float]]:
        source: dict[str, dict[str, float | None]] = {}
        prices: dict[str, float] = {}
        for item in coin_snapshots:
            source[item.coin_id] = {"market_cap": item.market_cap, "spot_volume": item.spot_volume}
            if item.price is not None:
                prices[item.coin_id] = item.price
        for item in market_snapshots:
            values = source.setdefault(item.coin_id, {})
            values["spot_volume"] = item.spot_volume or values.get("spot_volume")
            values["spread"] = item.spread
            values["bid_depth"] = item.bid_depth
            values["ask_depth"] = item.ask_depth
            if item.price is not None and item.coin_id not in prices:
                prices[item.coin_id] = item.price
        return {coin_id: RawMarketState(**values) for coin_id, values in source.items()}, prices

    async def _deliver(self, repository: ScannerRepository, alert_id: str, message: NotificationMessage) -> bool:
        outcomes = await asyncio.gather(self.notifier.telegram(message), self.notifier.discord(message), self.notifier.email(message))
        flattened = [outcome for item in outcomes for outcome in (item if isinstance(item, list) else [item]) if outcome is not None]
        if not flattened:
            return False
        successes = []
        for channel, destination, delivered, error in flattened:
            delivery_id = await repository.create_delivery(alert_id, channel, destination)
            await repository.finish_delivery(delivery_id, delivered, error)
            successes.append(delivered)
        return any(successes)
