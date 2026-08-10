from hawk_worker.models import CatalogCoin, CoinSnapshot, MarketSnapshot
from hawk_worker.providers import CoinGeckoPublicProvider
from hawk_worker.scanner import ScannerService


def test_states_exclude_assets_without_positive_market_cap_or_volume():
    states, prices = ScannerService._states(
        [
            CoinSnapshot("eligible", "ELG", 12.0, 50_000_000.0, 50_000.0, "coingecko"),
            CoinSnapshot("no-volume", "NOV", 5.0, 50_000_000.0, 0.0, "coingecko"),
            CoinSnapshot("no-market-cap", "NMC", 3.0, 0.0, 100_000.0, "coingecko"),
            CoinSnapshot("too-small", "SML", 2.0, 29_999_999.0, 100_000.0, "coingecko"),
            CoinSnapshot("too-large", "LRG", 20.0, 100_000_001.0, 100_000.0, "coingecko"),
        ],
        [],
    )

    assert set(states) == {"eligible"}
    assert prices == {"eligible": 12.0}


def test_binance_volume_can_complete_an_otherwise_eligible_coin_snapshot():
    states, _ = ScannerService._states(
        [CoinSnapshot("eligible", "ELG", 12.0, 50_000_000.0, 0.0, "coingecko")],
        [MarketSnapshot("eligible", "market", "ELGUSDT", 12.0, 200_000.0, None, None, None, "binance")],
    )

    assert states["eligible"].spot_volume == 200_000.0


def test_states_exclude_pegged_memecoin_or_other_ineligible_universe_assets():
    states, _ = ScannerService._states(
        [
            CoinSnapshot("stable", "USDX", 1.0, 50_000_000.0, 500_000.0, "coingecko"),
            CoinSnapshot("meme", "MEME", 1.0, 50_000_000.0, 500_000.0, "coingecko"),
        ],
        [
            MarketSnapshot("stable", "stable-market", "USDXUSDT", 1.0, 500_000.0, None, None, None, "binance"),
            MarketSnapshot("meme", "meme-market", "MEMEUSDT", 1.0, 500_000.0, None, None, None, "binance"),
        ],
        {"stable", "meme"},
    )

    assert states == {}


def test_memecoin_fallback_covers_high_confidence_meme_assets_in_current_market_range():
    """The scanner must not wait for a category refresh to hide known memecoins."""
    assert {
        "baby-doge-coin", "turbo", "comedian", "peanut-the-squirrel", "jelly-my-jelly", "the-black-bull",
    }.issubset(CoinGeckoPublicProvider.fallback_memecoin_ids)


def test_catalog_market_data_is_reused_without_a_second_coingecko_request():
    snapshots = ScannerService._catalog_snapshots(
        [CatalogCoin("candidate", "CND", "Candidate", 300, price=1.25, market_cap=50_000_000.0, spot_volume=800_000.0)],
        [{"id": "coin_1", "metadata": {"coingecko_id": "candidate"}}],
    )

    assert snapshots == [CoinSnapshot("coin_1", "CND", 1.25, 50_000_000.0, 800_000.0, "coingecko")]
