import asyncio
import logging
import math
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

logger = logging.getLogger(__name__)


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
                coin_snapshots, market_snapshots = await self._public_snapshots(coins, markets)
                await repository.persist_coin_snapshots(coin_snapshots, started_at)
                await repository.persist_market_snapshots(market_snapshots, started_at)
                excluded_coin_ids = {
                    coin["id"]
                    for coin in coins
                    if coin.get("asset_type") == "STABLECOIN"
                    or (isinstance(coin.get("metadata"), dict) and coin["metadata"].get("scanner_eligible") is False)
                }
                states, current_prices = self._states(
                    coin_snapshots,
                    market_snapshots,
                    excluded_coin_ids,
                    self.settings.min_target_market_cap_usd,
                    self.settings.max_target_market_cap_usd,
                )
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
        catalog_key = "hawk-scanner:catalog:v5"
        if await lock_client.get(catalog_key):
            return
        catalog_coins = []
        binance_markets = []
        try:
            catalog_coins = await self.coin_gecko.catalog(self.settings.coingecko_catalog_pages)
        except Exception as error:  # Public providers must not halt the scanner's next attempt.
            logger.warning("CoinGecko catalog unavailable", exc_info=error)
        if catalog_coins:
            await repository.upsert_catalog_coins(catalog_coins)
        try:
            binance_markets = await self.binance.catalog()
        except Exception as error:  # Binance is an independent public fallback.
            logger.warning("Binance catalog unavailable", exc_info=error)
        if binance_markets:
            await repository.upsert_binance_markets(binance_markets)
        if catalog_coins or binance_markets:
            await lock_client.set(catalog_key, "ready", ex=self.settings.catalog_refresh_seconds)

    async def _public_snapshots(
        self, coins: list[dict], markets: list[dict]
    ) -> tuple[list[CoinSnapshot], list[MarketSnapshot]]:
        """Use every available public feed without making one transient failure fatal."""
        coin_result, market_result = await asyncio.gather(
            self.coin_gecko.fetch(coins), self.binance.fetch(markets), return_exceptions=True
        )
        coin_snapshots = coin_result if isinstance(coin_result, list) else []
        market_snapshots = market_result if isinstance(market_result, list) else []
        if isinstance(coin_result, Exception):
            logger.warning("CoinGecko snapshots unavailable for this cycle", exc_info=coin_result)
        if isinstance(market_result, Exception):
            logger.warning("Binance snapshots unavailable for this cycle", exc_info=market_result)
        return coin_snapshots, market_snapshots

    @staticmethod
    def _states(
        coin_snapshots: list[CoinSnapshot], market_snapshots: list[MarketSnapshot], excluded_coin_ids: set[str] | None = None,
        min_market_cap: float = 30_000_000, max_market_cap: float = 100_000_000,
    ) -> tuple[dict[str, RawMarketState], dict[str, float]]:
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
        blocked = excluded_coin_ids or set()
        states = {
            coin_id: RawMarketState(**values)
            for coin_id, values in source.items()
            if coin_id not in blocked and ScannerService._is_eligible_for_ranking(values, min_market_cap, max_market_cap)
        }
        return states, {coin_id: price for coin_id, price in prices.items() if coin_id in states}

    @staticmethod
    def _is_eligible_for_ranking(
        values: dict[str, float | None], min_market_cap: float, max_market_cap: float,
    ) -> bool:
        """Accept only liquid $30M–$100M candidates by default, before Hawk Score calculation."""
        market_cap, spot_volume = values.get("market_cap"), values.get("spot_volume")
        return (
            market_cap is not None
            and spot_volume is not None
            and math.isfinite(market_cap)
            and math.isfinite(spot_volume)
            and min_market_cap <= market_cap <= max_market_cap
            and spot_volume > 0
        )

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
