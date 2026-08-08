from math import isclose

from src.domain.scoring.hawk_score import FeatureEvidence, HawkCalibration, HawkScoreEngine, RawMarketState


def test_score_is_bounded_and_weights_are_recalibrated_from_evidence():
    calibration = HawkCalibration(
        regime="adaptive",
        as_of="2026-08-08T00:00:00+00:00",
        feature_reference_values={
            "market_cap": [10.0, 100.0, 1_000.0],
            "spot_turnover": [0.01, 0.1, 0.4],
            "spread": [0.0001, 0.001, 0.01],
        },
        feature_evidence={
            "market_cap": FeatureEvidence(0.10, 0.05, 1.0),
            "spot_turnover": FeatureEvidence(0.25, 0.10, 1.0),
            "spread": FeatureEvidence(-0.20, 0.10, 1.0),
        },
        group_evidence={
            "valuation": FeatureEvidence(0.10, 0.05, 1.0),
            "liquidity": FeatureEvidence(0.20, 0.10, 1.0),
        },
    )

    result = HawkScoreEngine().calculate(
        RawMarketState(market_cap=100.0, spot_volume=40.0, spread=0.001), calibration
    )

    assert 0.0 <= result.score <= 100.0
    assert isclose(sum(result.feature_weights.values()), 1.0)
    assert result.feature_weights["market_cap"] != result.feature_weights["spot_turnover"]
    assert result.confidence == 1.0
