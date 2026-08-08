from dataclasses import dataclass
from math import log2, sqrt
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier


@dataclass(frozen=True)
class TrainingExample:
    snapshot_id: str
    coin_id: str
    observed_at: Any
    features: dict[str, Any]
    forward_return: float
    label: int


@dataclass
class TrainedXGBoostModel:
    model: XGBClassifier
    feature_names: list[str]
    positive_leaf_vectors: np.ndarray
    metrics: dict[str, float]
    hyperparameters: dict[str, Any]
    samples: int
    positive_samples: int


class XGBoostSimilarityTrainer:
    """Supervised event learner; no manual feature weights or contribution rules."""

    @staticmethod
    def _features(examples: Sequence[TrainingExample]) -> list[str]:
        return sorted({name for example in examples for name in example.features})

    @staticmethod
    def _matrix(examples: Sequence[TrainingExample], names: list[str]) -> np.ndarray:
        return np.asarray([[float(example.features.get(name, np.nan)) for name in names] for example in examples], dtype=float)

    @staticmethod
    def _labels(examples: Sequence[TrainingExample]) -> np.ndarray:
        return np.asarray([example.label for example in examples], dtype=int)

    @staticmethod
    def _hyperparameters(samples: int, positives: int, features: int) -> dict[str, Any]:
        if positives == 0 or positives == samples:
            raise ValueError("Daily training requires both breakout and non-breakout observations")
        return {
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "tree_method": "hist",
            "n_estimators": max(1, round(sqrt(samples * max(features, 1)))),
            "max_depth": max(1, round(log2(max(features, 1) + 1))),
            "learning_rate": 1 / sqrt(samples),
            "min_child_weight": samples / positives,
            "scale_pos_weight": (samples - positives) / positives,
            "subsample": positives / samples,
            "colsample_bytree": 1 / sqrt(features) if features else 1.0,
            "random_state": 0,
        }

    def train(self, examples: Sequence[TrainingExample]) -> TrainedXGBoostModel:
        ordered = sorted(examples, key=lambda item: item.observed_at)
        names = self._features(ordered)
        if not names:
            raise ValueError("Daily training requires at least one observed ML feature")
        matrix, labels = self._matrix(ordered, names), self._labels(ordered)
        positives = int(labels.sum())
        parameters = self._hyperparameters(len(ordered), positives, len(names))
        validation_probability: list[float] = []
        validation_label: list[int] = []
        folds = min(len(ordered) - 1, max(2, round(sqrt(len(ordered)))))
        if folds >= 2:
            for train_index, validation_index in TimeSeriesSplit(n_splits=folds).split(matrix):
                train_labels = labels[train_index]
                if len(np.unique(train_labels)) < 2:
                    continue
                fold_model = XGBClassifier(**parameters)
                fold_model.fit(matrix[train_index], train_labels)
                validation_probability.extend(fold_model.predict_proba(matrix[validation_index])[:, 1])
                validation_label.extend(labels[validation_index])
        metrics: dict[str, float] = {}
        if len(set(validation_label)) == 2:
            metrics["walk_forward_auc_roc"] = float(roc_auc_score(validation_label, validation_probability))
            metrics["walk_forward_average_precision"] = float(average_precision_score(validation_label, validation_probability))
        model = XGBClassifier(**parameters)
        model.fit(matrix, labels)
        positive_leaf_vectors = model.apply(matrix[labels == 1])
        return TrainedXGBoostModel(model, names, positive_leaf_vectors, metrics, parameters, len(ordered), positives)

    @staticmethod
    def save(model: TrainedXGBoostModel, artifact_directory: str, run_id: str) -> str:
        directory = Path(artifact_directory)
        directory.mkdir(parents=True, exist_ok=True)
        artifact = directory / f"{run_id}.json"
        model.model.save_model(artifact)
        return str(artifact)

    @staticmethod
    def similarity(model: TrainedXGBoostModel, snapshots: Sequence[dict[str, Any]]) -> list[dict[str, float | str]]:
        if not snapshots or not len(model.positive_leaf_vectors):
            return []
        matrix = np.asarray([
            [float(snapshot["features"].get(name, np.nan)) for name in model.feature_names] for snapshot in snapshots
        ], dtype=float)
        leaf_vectors = model.model.apply(matrix)
        probability = model.model.predict_proba(matrix)[:, 1]
        # Agreement happens in tree-leaf space, whose partitions and interactions are learned by XGBoost.
        agreement = (leaf_vectors[:, None, :] == model.positive_leaf_vectors[None, :, :]).mean(axis=(1, 2))
        return [
            {"coin_id": snapshot["coin_id"], "score": float(100 * agreement[index]),
             "probability": float(probability[index]), "agreement": float(agreement[index])}
            for index, snapshot in enumerate(snapshots)
        ]
