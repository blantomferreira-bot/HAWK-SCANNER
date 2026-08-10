from hawk_worker.models import CoinSnapshot, MarketSnapshot
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
