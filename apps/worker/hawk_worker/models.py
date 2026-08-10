from dataclasses import dataclass


@dataclass(frozen=True)
class CoinSnapshot:
    coin_id: str
    symbol: str
    price: float | None
    market_cap: float | None
    spot_volume: float | None
    source: str


@dataclass(frozen=True)
class MarketSnapshot:
    coin_id: str
    market_id: str
    symbol: str
    price: float | None
    spot_volume: float | None
    spread: float | None
    bid_depth: float | None
    ask_depth: float | None
    source: str


@dataclass(frozen=True)
class CatalogCoin:
    external_id: str
    symbol: str
    name: str
    market_cap_rank: int | None
    asset_type: str = "CRYPTOCURRENCY"
    scanner_eligible: bool = True
    classification_reason: str | None = None
    price: float | None = None
    market_cap: float | None = None
    spot_volume: float | None = None


@dataclass(frozen=True)
class CatalogMarket:
    symbol: str
    base_symbol: str
    quote_symbol: str
    exchange_code: str = "BINANCE"


@dataclass(frozen=True)
class NotificationMessage:
    coin_id: str
    symbol: str
    score: float
    threshold: float
    confidence: float
    ranking_position: int | None
