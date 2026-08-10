import asyncio
import json
import logging
from typing import Any

import httpx

from hawk_worker.models import CatalogCoin, CatalogMarket, CoinSnapshot, MarketSnapshot

logger = logging.getLogger(__name__)


def _metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


class CoinGeckoPublicProvider:
    """Coin catalog and bulk public market data, fetched in API-safe batches."""

    endpoint = "https://api.coingecko.com/api/v3/coins/markets"
    categories_endpoint = "https://api.coingecko.com/api/v3/coins/categories/list"
    fallback_stablecoin_ids = frozenset({
        "tether", "usd-coin", "dai", "usd1", "usd1-wlfi", "first-digital-usd", "paypal-usd", "ethena-usde", "usds",
        "global-dollar", "frax", "true-usd", "paxos-standard", "liquity-usd", "usdd", "usde",
        "royal-euro", "saturn-dollar", "jupusd", "chip-2", "straitsx-xusd", "unity-usd", "wrappedm-by-m0",
    })
    fallback_non_speculative_ids = frozenset({
        "pax-gold", "tether-gold", "spacex-bstocks-tokenized-stock", "micron-technology-bstock",
        "blackrock-usd-institutional-digital-liquidity-fund", "circle-internet-group-bstock",
        "circle-internet-group-ondo-tokenized-stock", "circle-xstock", "tesla-xstock", "sp500-xstock",
    })
    fallback_memecoin_ids = frozenset({
        "dogecoin", "shiba-inu", "pepe", "bonk", "dogwifcoin", "floki", "official-trump", "spx6900",
        "brett", "popcat", "mog-coin", "cat-in-a-dogs-world", "goatseus-maximus", "fartcoin", "banana-for-scale-2",
        "melania-meme", "baby-doge-coin", "turbo", "comedian", "peanut-the-squirrel", "jelly-my-jelly",
        "the-black-bull", "book-of-meme", "dog-go-to-the-moon-rune", "dogelon-mars", "cash-cat", "baby-claw",
    })

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        # The public endpoint works without a key. A configured key uses the documented Pro header.
        return {"x-cg-pro-api-key": self.api_key} if self.api_key else {}

    async def catalog(self, pages: int) -> list[CatalogCoin]:
        if pages < 1:
            raise ValueError("COINGECKO_CATALOG_PAGES must be at least 1")
        async with httpx.AsyncClient(timeout=30) as client:
            classifications = await self._catalog_classifications(client, pages)
            responses = []
            for page in range(1, pages + 1):
                try:
                    response = await client.get(
                        self.endpoint,
                        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250, "page": page},
                        headers=self.headers,
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    if error.response.status_code != 429:
                        raise
                    logger.warning(
                        "CoinGecko catalog rate limited; using the collected catalog pages",
                        extra={"requested_pages": pages, "completed_pages": page - 1},
                    )
                    break
                responses.extend(response.json())
        return [
            CatalogCoin(
                external_id=str(item["id"]),
                symbol=str(item["symbol"]).upper(),
                name=str(item["name"]),
                market_cap_rank=item.get("market_cap_rank"),
                asset_type="STABLECOIN" if classifications.get(str(item["id"]), {}).get("stablecoin") else "CRYPTOCURRENCY",
                scanner_eligible=not classifications.get(str(item["id"]), {}).get("excluded", False),
                classification_reason=classifications.get(str(item["id"]), {}).get("reason"),
                price=item.get("current_price"),
                market_cap=item.get("market_cap"),
                spot_volume=item.get("total_volume"),
            )
            for item in responses
            if item.get("id") and item.get("symbol") and item.get("name")
        ]

    async def _catalog_classifications(self, client: httpx.AsyncClient, catalog_pages: int) -> dict[str, dict[str, Any]]:
        """Classify scanner assets from CoinGecko's primary category per exclusion type.

        The unauthenticated CoinGecko endpoint has a shared request budget. It
        exposes many overlapping meme subcategories, and requesting every one
        can consume the entire budget before market data is collected. The
        top-level Meme category contains the market-cap ordered universe
        relevant to the scanner, so it is the dynamic classification source;
        stablecoin and tokenized-asset safeguards remain in the fallback set
        until a higher-quota CoinGecko key is configured.
        """
        classifications: dict[str, dict[str, Any]] = {
            coin_id: {"stablecoin": True, "excluded": True, "reason": "stablecoin-fallback"}
            for coin_id in self.fallback_stablecoin_ids
        }
        classifications.update({
            coin_id: {"stablecoin": False, "excluded": True, "reason": "rwa-fallback"}
            for coin_id in self.fallback_non_speculative_ids
        })
        classifications.update({
            coin_id: {"stablecoin": False, "excluded": True, "reason": "memecoin-fallback"}
            for coin_id in self.fallback_memecoin_ids
        })
        try:
            categories_response = await client.get(self.categories_endpoint, headers=self.headers)
            categories_response.raise_for_status()
            categories = categories_response.json()
            candidates: dict[str, list[tuple[int, str, str, bool]]] = {
                "memecoin": [], "stablecoin": [], "non-speculative-category": [],
            }
            for category in categories:
                category_id = str(category.get("category_id", ""))
                name = str(category.get("name", "")).lower()
                if not category_id:
                    continue
                normalized_name = " ".join(name.split())
                if "stablecoin" in normalized_name:
                    candidates["stablecoin"].append(
                        (0 if normalized_name in {"stablecoin", "stablecoins"} else 1, category_id, "stablecoin", True)
                    )
                elif "real world asset" in name or "rwa" in name or "tokenized" in name:
                    candidates["non-speculative-category"].append(
                        (0 if "real world asset" in normalized_name else 1, category_id, "non-speculative-category", False)
                    )
                elif "meme" in normalized_name:
                    candidates["memecoin"].append(
                        (0 if normalized_name in {"meme", "memes"} else 1, category_id, "memecoin-category", False)
                    )

            # Keep one dynamic category call available during a catalog refresh
            # so the subsequent market pages remain within the public quota.
            request_budget = min(1, max(1, catalog_pages))
            targets: list[tuple[str, str, bool]] = []
            for category_kind in ("memecoin",):
                if not candidates[category_kind]:
                    continue
                _, category_id, reason, is_stablecoin = min(candidates[category_kind])
                targets.append((category_id, reason, is_stablecoin))

            for category_id, reason, is_stablecoin in targets[:request_budget]:
                try:
                    response = await client.get(
                        self.endpoint,
                        params={"vs_currency": "usd", "category": category_id, "per_page": 250, "page": 1},
                        headers=self.headers,
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    if error.response.status_code == 429:
                        logger.warning("CoinGecko classification rate limited; retaining completed classifications")
                        break
                    logger.warning("CoinGecko classification category unavailable", exc_info=error)
                    continue
                category_coins = response.json()
                if not isinstance(category_coins, list):
                    continue
                for item in category_coins:
                    coin_id = item.get("id")
                    if coin_id:
                        classifications[str(coin_id)] = {
                            "stablecoin": is_stablecoin,
                            "excluded": True,
                            "reason": reason,
                        }
        except httpx.HTTPError as error:
            logger.warning("CoinGecko universe classification unavailable; applying stablecoin safety fallback", exc_info=error)
        return classifications

    async def fetch(self, coins: list[dict[str, Any]]) -> list[CoinSnapshot]:
        mapped = {
            str(_metadata(coin.get("metadata")).get("coingecko_id")): coin
            for coin in coins
            if _metadata(coin.get("metadata")).get("coingecko_id")
        }
        if not mapped:
            return []
        payload: list[dict[str, Any]] = []
        external_ids = list(mapped)
        async with httpx.AsyncClient(timeout=30) as client:
            for offset in range(0, len(external_ids), 250):
                try:
                    response = await client.get(
                        self.endpoint,
                        params={"vs_currency": "usd", "ids": ",".join(external_ids[offset:offset + 250]), "per_page": 250},
                        headers=self.headers,
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    if error.response.status_code == 429:
                        logger.warning("CoinGecko snapshots rate limited; retaining completed snapshot batches")
                        break
                    raise
                payload.extend(response.json())
        snapshots: list[CoinSnapshot] = []
        for item in payload:
            coin = mapped.get(item.get("id"))
            if coin is None:
                continue
            snapshots.append(CoinSnapshot(
                coin_id=coin["id"], symbol=coin["symbol"], price=item.get("current_price"),
                market_cap=item.get("market_cap"), spot_volume=item.get("total_volume"), source="coingecko",
            ))
        return snapshots


class BinancePublicProvider:
    """Bulk spot ticker and best-book data for configured Binance markets."""

    ticker_endpoint = "https://api.binance.com/api/v3/ticker/24hr"
    book_endpoint = "https://api.binance.com/api/v3/ticker/bookTicker"
    exchange_info_endpoint = "https://api.binance.com/api/v3/exchangeInfo"

    async def catalog(self) -> list[CatalogMarket]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.exchange_info_endpoint)
            response.raise_for_status()
        return [
            CatalogMarket(symbol=item["symbol"], base_symbol=item["baseAsset"], quote_symbol=item["quoteAsset"])
            for item in response.json().get("symbols", [])
            if item.get("status") == "TRADING"
            and item.get("isSpotTradingAllowed", False)
            and item.get("quoteAsset") == "USDT"
            and item.get("baseAsset") != "USDT"
        ]

    async def fetch(self, markets: list[dict[str, Any]]) -> list[MarketSnapshot]:
        active = {market["symbol"]: market for market in markets if market.get("exchange_code") == "BINANCE"}
        if not active:
            return []
        async with httpx.AsyncClient(timeout=30) as client:
            ticker_response, book_response = await asyncio.gather(client.get(self.ticker_endpoint), client.get(self.book_endpoint))
            ticker_response.raise_for_status()
            book_response.raise_for_status()
        tickers = {item["symbol"]: item for item in ticker_response.json() if item.get("symbol") in active}
        books = {item["symbol"]: item for item in book_response.json() if item.get("symbol") in active}
        result: list[MarketSnapshot] = []
        for symbol, market in active.items():
            ticker, book = tickers.get(symbol), books.get(symbol)
            if ticker is None:
                continue
            bid = float(book["bidPrice"]) if book and float(book["bidPrice"]) > 0 else None
            ask = float(book["askPrice"]) if book and float(book["askPrice"]) > 0 else None
            midpoint = (bid + ask) / 2 if bid is not None and ask is not None else None
            spread = (ask - bid) / midpoint if midpoint else None
            result.append(MarketSnapshot(
                coin_id=market["base_coin_id"], market_id=market["id"], symbol=symbol,
                price=float(ticker["lastPrice"]), spot_volume=float(ticker["quoteVolume"]), spread=spread,
                bid_depth=float(book["bidQty"]) if book else None, ask_depth=float(book["askQty"]) if book else None,
                source="binance",
            ))
        return result
