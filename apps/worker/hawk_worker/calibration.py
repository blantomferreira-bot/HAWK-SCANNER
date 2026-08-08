from math import sqrt
from statistics import median
from typing import Mapping

from hawk_worker.bootstrap import add_api_to_path

add_api_to_path()

from src.domain.scoring.hawk_score import (  # noqa: E402
    FEATURE_GROUPS,
    FeatureEvidence,
    HawkCalibration,
    HawkFeatureBuilder,
    RawMarketState,
)


def _average_rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        next_cursor = cursor + 1
        while next_cursor < len(indexed) and indexed[next_cursor][1] == indexed[cursor][1]:
            next_cursor += 1
        rank = (cursor + 1 + next_cursor) / 2
        for original_index, _ in indexed[cursor:next_cursor]:
            ranks[original_index] = rank
        cursor = next_cursor
    return ranks


def _spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    left, right = _average_rank([pair[0] for pair in pairs]), _average_rank([pair[1] for pair in pairs])
    left_mean, right_mean = sum(left) / len(left), sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    denominator = sqrt(sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right))
    return numerator / denominator if denominator else None


class DynamicCalibrator:
    """Recomputes evidence from the complete available cross-section each scan.

    Realized return is the return observed since the prior scan. It is deliberately
    not substituted by a constant during warm-up; without evidence, no score is emitted.
    """

    def calibrate(self, states: Mapping[str, RawMarketState], realized_returns: Mapping[str, float], as_of: str) -> HawkCalibration:
        feature_values = {coin_id: HawkFeatureBuilder.build(state) for coin_id, state in states.items()}
        reference_values: dict[str, list[float]] = {}
        evidence: dict[str, FeatureEvidence] = {}

        for feature in FEATURE_GROUPS:
            universe = [values[feature] for values in feature_values.values() if feature in values]
            pairs = [(values[feature], realized_returns[coin_id]) for coin_id, values in feature_values.items()
                     if feature in values and coin_id in realized_returns]
            correlation = _spearman(pairs)
            if correlation is None:
                continue
            sample_size = len(pairs)
            variance = (1 - correlation * correlation) / (sample_size - 2) if sample_size > 2 else 0.0
            standard_error = sqrt(variance) if variance > 0 else 0.0
            evidence[feature] = FeatureEvidence(correlation, standard_error, len(pairs) / len(states) if states else 0.0)
            reference_values[feature] = universe

        grouped: dict[str, list[FeatureEvidence]] = {}
        for feature, feature_evidence in evidence.items():
            if feature_evidence.strength > 0:
                grouped.setdefault(FEATURE_GROUPS[feature], []).append(feature_evidence)
        group_evidence = {
            group: FeatureEvidence(
                information_coefficient=median(item.information_coefficient for item in items),
                standard_error=median(item.standard_error for item in items),
                coverage=median(item.coverage for item in items),
            )
            for group, items in grouped.items()
        }
        return HawkCalibration("adaptive", as_of, reference_values, evidence, group_evidence)
