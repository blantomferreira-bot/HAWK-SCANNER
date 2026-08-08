import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from hawk_worker.bootstrap import add_api_to_path
from hawk_worker.config import ScannerSettings
from hawk_worker.ml.repository import MlRepository
from hawk_worker.ml.trainer import TrainingExample, XGBoostSimilarityTrainer

add_api_to_path()

from src.infrastructure.database import SessionLocal  # noqa: E402


def _feature_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    return {}


class DailyLearningService:
    def __init__(self, settings: ScannerSettings) -> None:
        self.settings = settings
        self.trainer = XGBoostSimilarityTrainer()

    @dataclass(frozen=True)
    class Target:
        name: str
        window_days: int
        return_threshold: float

        @property
        def label_definition(self) -> str:
            return f"forward_return_{self.window_days}d > {self.return_threshold * 100:g}%"

    targets = (
        Target("breakout-wide-xgboost", 90, 3.0),
        Target("explosive-discovery-xgboost", 30, 5.0),
    )

    async def run_daily(self) -> dict[str, Any]:
        observed_at = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        outcomes: list[dict[str, int | str]] = []
        for target in self.targets:
            outcomes.append(await self._train_target(target, observed_at))
        return {"status": "COMPLETED", "models": outcomes}

    async def _train_target(self, target: Target, observed_at: datetime) -> dict[str, int | str]:
        run_id = f"mlr_{target.name}_{uuid4().hex}"
        async with SessionLocal() as session:
            repository = MlRepository(session)
            await repository.start_training_run(run_id, target.name, target.label_definition, target.window_days)
            try:
                current_rows = await repository.collect_window_features(observed_at, target.window_days)
                await repository.save_feature_snapshots(current_rows, observed_at, target.window_days)
                rows = await repository.labeled_examples(observed_at, target.window_days)
                examples = [TrainingExample(
                    snapshot_id=row["id"], coin_id=row["coin_id"], observed_at=row["observed_at"],
                    features=_feature_mapping(row["features"]), forward_return=float(row["forward_return"]),
                    label=int(float(row["forward_return"]) > target.return_threshold),
                ) for row in rows]
                if not examples:
                    await repository.finish_training_run(run_id, "WARMING_UP", [], 0, 0, {}, {}, None, error=f"No {target.window_days}-day labeled observations yet")
                    return {"run_id": run_id, "status": "WARMING_UP", "samples": 0}
                trained = self.trainer.train(examples)
                artifact_uri = self.trainer.save(trained, self.settings.ml_artifact_dir, run_id)
                current_snapshots = await repository.current_feature_snapshots(observed_at, target.window_days)
                for snapshot in current_snapshots:
                    snapshot["features"] = _feature_mapping(snapshot["features"])
                similarities = self.trainer.similarity(trained, current_snapshots)
                await repository.persist_similarity_scores(run_id, similarities, observed_at)
                await repository.finish_training_run(
                    run_id, "COMPLETED", trained.feature_names, trained.samples, trained.positive_samples,
                    trained.metrics, trained.hyperparameters, artifact_uri,
                    min(example.observed_at for example in examples), max(example.observed_at for example in examples),
                )
                return {"run_id": run_id, "status": "COMPLETED", "samples": trained.samples,
                        "positive_samples": trained.positive_samples, "similarity_scores": len(similarities)}
            except ValueError as error:
                await repository.finish_training_run(run_id, "WARMING_UP", [], 0, 0, {}, {}, None, error=str(error))
                return {"run_id": run_id, "status": "WARMING_UP", "reason": str(error)}
            except Exception as error:
                await repository.finish_training_run(run_id, "FAILED", [], 0, 0, {}, {}, None, error=str(error))
                raise
