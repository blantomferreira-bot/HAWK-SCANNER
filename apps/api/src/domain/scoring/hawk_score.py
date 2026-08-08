"""Regime-calibrated, dynamically weighted HAWK Score (0-100)."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isfinite
from typing import Mapping, Sequence


FEATURE_GROUPS: Mapping[str, str] = {
    "float_ratio": "supply",
    "fdv_to_market_cap": "valuation",
    "market_cap": "valuation",
    "open_interest_to_market_cap": "derivatives",
    "funding": "derivatives",
    "liquidation_imbalance": "derivatives",
    "estimated_leverage_ratio": "derivatives",
    "long_short_ratio": "derivatives",
    "exchange_netflow_to_market_cap": "flows",
    "whale_activity_to_market_cap": "flows",
    "spot_turnover": "liquidity",
    "perp_turnover": "liquidity",
    "spread": "liquidity",
    "order_book_imbalance": "liquidity",
    "holder_growth": "on_chain",
    "top_wallet_share": "on_chain",
    "active_address_growth": "on_chain",
    "dormancy": "on_chain",
    "sopr": "on_chain",
    "mvrv": "on_chain",
    "nupl": "on_chain",
    "cvd": "on_chain",
    "tvl": "defi",
    "tvl_to_market_cap": "defi",
    "unlock_to_float": "supply",
    "narrative": "attention",
}


@dataclass(frozen=True)
class FeatureEvidence:
    """Walk-forward evidence of one feature inside the current market regime.

    `information_coefficient` is the out-of-sample Spearman correlation between
    this feature and the selected forward return horizon. `standard_error` comes
    from the same walk-forward/bootstrap procedure; `coverage` is the observed
    share of valid observations in that calibration sample.
    """

    information_coefficient: float
    standard_error: float
    coverage: float

    @property
    def strength(self) -> float:
        if not all(isfinite(value) for value in (self.information_coefficient, self.standard_error, self.coverage)):
            return 0.0
        if self.standard_error <= 0 or self.coverage <= 0:
            return 0.0
        return abs(self.information_coefficient) * self.coverage / self.standard_error


@dataclass(frozen=True)
class HawkCalibration:
    """Inputs produced by the calibration worker for one market regime and horizon."""

    regime: str
    as_of: str
    feature_reference_values: Mapping[str, Sequence[float]]
    feature_evidence: Mapping[str, FeatureEvidence]
    group_evidence: Mapping[str, FeatureEvidence]


@dataclass(frozen=True)
class RawMarketState:
    """Raw public-data inputs. None means unavailable and is never imputed."""

    free_float: float | None = None
    total_supply: float | None = None
    fdv: float | None = None
    market_cap: float | None = None
    open_interest: float | None = None
    funding: float | None = None
    long_liquidations: float | None = None
    short_liquidations: float | None = None
    exchange_netflow: float | None = None
    whale_activity: float | None = None
    holders: float | None = None
    previous_holders: float | None = None
    tvl: float | None = None
    spot_volume: float | None = None
    perp_volume: float | None = None
    spread: float | None = None
    bid_depth: float | None = None
    ask_depth: float | None = None
    top_wallet_balance: float | None = None
    upcoming_unlock: float | None = None
    narrative: float | None = None
    active_addresses: float | None = None
    previous_active_addresses: float | None = None
    dormancy: float | None = None
    sopr: float | None = None
    mvrv: float | None = None
    nupl: float | None = None
    cvd: float | None = None
    exchange_reserves: float | None = None
    long_short_ratio: float | None = None


@dataclass(frozen=True)
class HawkScoreResult:
    score: float
    confidence: float
    regime: str
    as_of: str
    feature_values: Mapping[str, float]
    normalized_signals: Mapping[str, float]
    feature_weights: Mapping[str, float]
    group_weights: Mapping[str, float]
    contributions: Mapping[str, float]


def _finite(value: float | None) -> float | None:
    return value if value is not None and isfinite(value) else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    numerator, denominator = _finite(numerator), _finite(denominator)
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _difference_over_sum(left: float | None, right: float | None) -> float | None:
    left, right = _finite(left), _finite(right)
    if left is None or right is None or left + right == 0:
        return None
    return (left - right) / (left + right)


def _growth(current: float | None, previous: float | None) -> float | None:
    current, previous = _finite(current), _finite(previous)
    if current is None or previous is None or previous <= 0:
        return None
    return (current - previous) / previous


class DynamicNormalizer:
    """Cross-sectional empirical CDF. No fixed clipping bounds or thresholds."""

    @staticmethod
    def percentile(value: float, reference: Sequence[float]) -> float | None:
        clean = sorted(item for item in reference if isfinite(item))
        if not clean or not isfinite(value):
            return None
        lower = sum(item < value for item in clean)
        equal = sum(item == value for item in clean)
        average_rank = lower + (equal + 1) / 2
        return average_rank / (len(clean) + 1)


class HawkFeatureBuilder:
    """Transforms raw public data into dimensionless, comparable feature values."""

    @staticmethod
    def build(state: RawMarketState) -> dict[str, float]:
        market_cap = state.market_cap
        values: dict[str, float | None] = {
            "float_ratio": _ratio(state.free_float, state.total_supply),
            "fdv_to_market_cap": _ratio(state.fdv, market_cap),
            "market_cap": _finite(market_cap),
            "open_interest_to_market_cap": _ratio(state.open_interest, market_cap),
            "funding": _finite(state.funding),
            "liquidation_imbalance": _difference_over_sum(state.short_liquidations, state.long_liquidations),
            "estimated_leverage_ratio": _ratio(state.open_interest, state.exchange_reserves),
            "long_short_ratio": _finite(state.long_short_ratio),
            "exchange_netflow_to_market_cap": _ratio(state.exchange_netflow, market_cap),
            "whale_activity_to_market_cap": _ratio(state.whale_activity, market_cap),
            "holder_growth": _growth(state.holders, state.previous_holders),
            "tvl": _finite(state.tvl),
            "tvl_to_market_cap": _ratio(state.tvl, market_cap),
            "spot_turnover": _ratio(state.spot_volume, market_cap),
            "perp_turnover": _ratio(state.perp_volume, state.open_interest),
            "spread": _finite(state.spread),
            "order_book_imbalance": _difference_over_sum(state.bid_depth, state.ask_depth),
            "top_wallet_share": _ratio(state.top_wallet_balance, state.free_float),
            "unlock_to_float": _ratio(state.upcoming_unlock, state.free_float),
            "narrative": _finite(state.narrative),
            "active_address_growth": _growth(state.active_addresses, state.previous_active_addresses),
            "dormancy": _finite(state.dormancy),
            "sopr": _finite(state.sopr),
            "mvrv": _finite(state.mvrv),
            "nupl": _finite(state.nupl),
            "cvd": _finite(state.cvd),
        }
        return {name: value for name, value in values.items() if value is not None}


class HawkScoreEngine:
    """Calculates a bounded score from a calibration supplied by a worker.

    The engine intentionally refuses to invent a score when predictive evidence
    or a reference universe is missing. This prevents hidden static fallbacks.
    """

    def calculate(self, state: RawMarketState, calibration: HawkCalibration) -> HawkScoreResult:
        raw_values = HawkFeatureBuilder.build(state)
        active: dict[str, tuple[float, float, FeatureEvidence, str]] = {}

        for name, value in raw_values.items():
            evidence = calibration.feature_evidence.get(name)
            reference = calibration.feature_reference_values.get(name)
            group = FEATURE_GROUPS.get(name)
            if evidence is None or reference is None or group is None or evidence.strength == 0:
                continue
            percentile = DynamicNormalizer.percentile(value, reference)
            if percentile is None:
                continue
            direction = 1.0 if evidence.information_coefficient >= 0 else -1.0
            normalized_signal = direction * (2 * percentile - 1)
            active[name] = (value, normalized_signal, evidence, group)

        group_members: dict[str, list[str]] = {}
        for name, (_, _, _, group) in active.items():
            group_members.setdefault(group, []).append(name)

        group_strengths = {
            group: calibration.group_evidence[group].strength
            for group in group_members
            if group in calibration.group_evidence and calibration.group_evidence[group].strength > 0
        }
        if not group_strengths:
            raise ValueError("Hawk Score requires calibrated evidence for at least one active feature group")

        group_total = fsum(group_strengths.values())
        group_weights = {group: strength / group_total for group, strength in group_strengths.items()}
        feature_weights: dict[str, float] = {}

        for group, group_weight in group_weights.items():
            members = [name for name in group_members[group] if active[name][2].strength > 0]
            member_total = fsum(active[name][2].strength for name in members)
            for name in members:
                feature_weights[name] = group_weight * active[name][2].strength / member_total

        contributions = {name: feature_weights[name] * active[name][1] for name in feature_weights}
        centered_score = fsum(contributions.values())
        score = 100 * (centered_score + 1) / 2
        confidence = fsum(group_weights[group] * calibration.group_evidence[group].coverage for group in group_weights)

        return HawkScoreResult(
            score=score,
            confidence=confidence,
            regime=calibration.regime,
            as_of=calibration.as_of,
            feature_values={name: active[name][0] for name in feature_weights},
            normalized_signals={name: active[name][1] for name in feature_weights},
            feature_weights=feature_weights,
            group_weights=group_weights,
            contributions=contributions,
        )
