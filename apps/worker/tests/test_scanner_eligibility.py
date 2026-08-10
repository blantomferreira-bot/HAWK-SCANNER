from hawk_worker.models import CoinSnapshot, MarketSnapshot
from hawk_worker.scanner import ScannerService


def test_states_exclude_assets_without_positive_market_cap_or_volume():
    states, prices = ScannerService._states(
        [
            CoinSnapshot("eligible", "ELG", 12.0, 1_000_000.0, 50_000.0, "coingecko"),
            CoinSnapshot("no-volume", "NOV", 5.0, 1_000_000.0, 0.0, "coingecko"),
            CoinSnapshot("no-market-cap", "NMC", 3.0, 0.0, 100_000.0, "coingecko"),
        ],
        [],
    )

    assert set(states) == {"eligible"}
    assert prices == {"eligible": 12.0}


def test_binance_volume_can_complete_an_otherwise_eligible_coin_snapshot():
    states, _ = ScannerService._states(
        [CoinSnapshot("eligible", "ELG", 12.0, 1_000_000.0, 0.0, "coingecko")],
        [MarketSnapshot("eligible", "market", "ELGUSDT", 12.0, 200_000.0, None, None, None, "binance")],
    )

    assert states["eligible"].spot_volume == 200_000.0
