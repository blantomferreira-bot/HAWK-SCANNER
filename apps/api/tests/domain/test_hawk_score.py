from src.domain.scoring.hawk_score import FeatureEvidence, HawkCalibration, HawkScoreEngine, RawMarketState


def evidence(ic: float) -> FeatureEvidence:
    return FeatureEvidence(information_coefficient=ic, standard_error=abs(ic), coverage=1.0)


def calibration() -> HawkCalibration:
    return HawkCalibration(
        regime="high-volatility",
        as_of="2026-08-07T12:00:00Z",
        feature_reference_values={"funding": [-0.02, 0.0, 0.03], "spot_turnover": [0.1, 0.4, 0.9]},
        feature_evidence={"funding": evidence(-0.4), "spot_turnover": evidence(0.3)},
        group_evidence={"derivatives": evidence(-0.4), "liquidity": evidence(0.3)},
    )


def test_hawk_score_is_bounded_and_explainable():
    state = RawMarketState(market_cap=100, funding=-0.02, spot_volume=90)
    result = HawkScoreEngine().calculate(state, calibration())

    assert 0 <= result.score <= 100
    assert set(result.feature_weights) == {"funding", "spot_turnover"}
    assert abs(sum(result.feature_weights.values()) - 1) < 1e-12
    assert abs(sum(result.group_weights.values()) - 1) < 1e-12


def test_missing_data_is_not_imputed():
    result = HawkScoreEngine().calculate(RawMarketState(funding=-0.02), calibration())

    assert set(result.feature_values) == {"funding"}
