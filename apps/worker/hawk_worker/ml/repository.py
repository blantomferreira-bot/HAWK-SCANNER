import json
from datetime import datetime, timedelta
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class MlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def collect_window_features(self, observed_at: datetime, window_days: int) -> list[dict[str, Any]]:
        window_start = observed_at - timedelta(days=window_days)
        result = await self.session.execute(text(
            """SELECT c.id AS coin_id, price.close AS reference_price,
                 funding.mean_value AS funding_mean_90d, funding.std_value AS funding_std_90d,
                 oi.mean_value AS open_interest_mean_90d, oi.change_ratio AS open_interest_change_90d,
                 whales.transfer_value AS whale_transfer_value_90d, whales.transfer_count AS whale_transfer_count_90d,
                 onchain.active_addresses AS active_addresses_90d, onchain.transaction_count AS transaction_count_90d,
                 volume.spot_volume AS volume_90d, volume.volume_volatility AS volume_volatility_90d,
                 wallets.wallet_count AS wallet_count, wallets.whale_wallet_count AS whale_wallet_count,
                 custom.narrative AS narrative_90d, custom.unlock_pressure AS unlock_pressure_90d,
                 custom.float_ratio AS float_ratio
               FROM coins c
               LEFT JOIN LATERAL (
                 SELECT close FROM history WHERE coin_id = c.id AND market_id IS NULL AND closed_at <= :as_of
                 ORDER BY closed_at DESC LIMIT 1
               ) price ON true
               LEFT JOIN LATERAL (
                 SELECT avg(rate) AS mean_value, stddev_pop(rate) AS std_value FROM funding f
                 JOIN markets m ON m.id = f.market_id WHERE m.base_coin_id = c.id AND f.observed_at BETWEEN :window_start AND :as_of
               ) funding ON true
               LEFT JOIN LATERAL (
                 SELECT avg(value_usd) AS mean_value,
                   (max(value_usd) - min(value_usd)) / NULLIF(min(value_usd), 0) AS change_ratio
                 FROM open_interest oi JOIN markets m ON m.id = oi.market_id
                 WHERE m.base_coin_id = c.id AND oi.observed_at BETWEEN :window_start AND :as_of
               ) oi ON true
               LEFT JOIN LATERAL (
                 SELECT sum(value_usd) AS transfer_value, count(*) AS transfer_count FROM transfers t
                 WHERE t.coin_id = c.id AND t.occurred_at BETWEEN :window_start AND :as_of
               ) whales ON true
               LEFT JOIN LATERAL (
                 SELECT avg(value) FILTER (WHERE type = 'ACTIVE_ADDRESSES') AS active_addresses,
                   avg(value) FILTER (WHERE type = 'TRANSACTION_COUNT') AS transaction_count
                 FROM metrics WHERE coin_id = c.id AND observed_at BETWEEN :window_start AND :as_of
               ) onchain ON true
               LEFT JOIN LATERAL (
                 SELECT avg(value) FILTER (WHERE type = 'VOLUME') AS spot_volume,
                   stddev_pop(value) FILTER (WHERE type = 'VOLUME') AS volume_volatility
                 FROM metrics WHERE coin_id = c.id AND market_id IS NULL AND observed_at BETWEEN :window_start AND :as_of
               ) volume ON true
               LEFT JOIN LATERAL (
                 SELECT count(*) AS wallet_count, count(wh.id) AS whale_wallet_count FROM wallets w
                 LEFT JOIN whales wh ON wh.wallet_id = w.id WHERE w.coin_id = c.id
               ) wallets ON true
               LEFT JOIN LATERAL (
                 SELECT max(value) FILTER (WHERE metadata->>'hawk_feature' = 'narrative') AS narrative,
                   max(value) FILTER (WHERE metadata->>'hawk_feature' = 'unlock_pressure') AS unlock_pressure,
                   max(value) FILTER (WHERE metadata->>'hawk_feature' = 'float_ratio') AS float_ratio
                 FROM metrics WHERE coin_id = c.id AND observed_at BETWEEN :window_start AND :as_of
               ) custom ON true
               WHERE c.is_active = true"""
        ), {"as_of": observed_at, "window_start": window_start})
        rows = [dict(row) for row in result.mappings().all()]
        aggregates = await self.session.execute(text(
            """SELECT coin_id, type::text AS metric_type, avg(value) AS mean_value, stddev_pop(value) AS std_value,
                      min(value) AS min_value, max(value) AS max_value, count(*) AS observations,
                      (array_agg(value ORDER BY observed_at ASC))[1] AS first_value,
                      (array_agg(value ORDER BY observed_at DESC))[1] AS last_value,
                      (max(value) - min(value)) / NULLIF(min(value), 0) AS range_ratio
               FROM metrics WHERE observed_at BETWEEN :window_start AND :as_of
               GROUP BY coin_id, type"""
        ), {"as_of": observed_at, "window_start": window_start})
        by_coin = {row["coin_id"]: row for row in rows}
        for aggregate in aggregates.mappings().all():
            row = by_coin.get(aggregate["coin_id"])
            if row is None:
                continue
            prefix = f"metric_{aggregate['metric_type'].lower()}"
            for name in ("mean_value", "std_value", "min_value", "max_value", "observations", "first_value", "last_value", "range_ratio"):
                value = aggregate[name]
                if value is not None:
                    row[f"{prefix}_{name}"] = value
        return rows

    async def save_feature_snapshots(self, rows: list[dict[str, Any]], observed_at: datetime, window_days: int) -> None:
        window_start = observed_at - timedelta(days=window_days)
        for row in rows:
            features = {key: value for key, value in row.items() if key not in {"coin_id", "reference_price"} and value is not None}
            await self.session.execute(text(
                """INSERT INTO ml_feature_snapshots (id, coin_id, observed_at, window_start_at, window_days, reference_price, features, created_at)
                   VALUES (:id, :coin_id, :observed_at, :window_start_at, :window_days, :reference_price, CAST(:features AS jsonb), now())
                   ON CONFLICT (coin_id, observed_at, window_days) DO NOTHING"""
            ), {"id": f"mlf_{uuid4().hex}", "coin_id": row["coin_id"], "observed_at": observed_at,
                "window_start_at": window_start, "window_days": window_days, "reference_price": row.get("reference_price"), "features": json.dumps(features)})
        await self.session.commit()

    async def labeled_examples(self, as_of: datetime, window_days: int) -> list[dict[str, Any]]:
        result = await self.session.execute(text(
            """SELECT fs.id, fs.coin_id, fs.observed_at, fs.features,
                      (future_price.close / fs.reference_price - 1) AS forward_return
               FROM ml_feature_snapshots fs
               JOIN LATERAL (
                 SELECT close FROM history h WHERE h.coin_id = fs.coin_id AND h.market_id IS NULL
                   AND h.closed_at >= fs.observed_at + (:window_days * interval '1 day')
                 ORDER BY h.closed_at ASC LIMIT 1
               ) future_price ON true
               WHERE fs.reference_price > 0 AND fs.window_days = :window_days
                 AND fs.observed_at + (:window_days * interval '1 day') <= :as_of
               ORDER BY fs.observed_at, fs.coin_id"""
        ), {"as_of": as_of, "window_days": window_days})
        return [dict(row) for row in result.mappings().all()]

    async def current_feature_snapshots(self, observed_at: datetime, window_days: int) -> list[dict[str, Any]]:
        result = await self.session.execute(text(
            "SELECT id, coin_id, features FROM ml_feature_snapshots WHERE observed_at = :observed_at AND window_days = :window_days ORDER BY coin_id"
        ), {"observed_at": observed_at, "window_days": window_days})
        return [dict(row) for row in result.mappings().all()]

    async def start_training_run(self, run_id: str, model_type: str, label_definition: str, window_days: int) -> None:
        await self.session.execute(text(
            """INSERT INTO ml_training_runs (id, status, model_type, label_definition, window_days, feature_names, created_at)
               VALUES (:id, 'RUNNING', :model_type, :label_definition, :window_days, ARRAY[]::text[], now())"""
        ), {"id": run_id, "model_type": model_type, "label_definition": label_definition, "window_days": window_days})
        await self.session.commit()

    async def finish_training_run(self, run_id: str, status: str, feature_names: list[str], samples: int, positive_samples: int,
                                  metrics: Mapping[str, Any], hyperparameters: Mapping[str, Any], artifact_uri: str | None,
                                  training_start_at: datetime | None = None, training_end_at: datetime | None = None,
                                  error: str | None = None) -> None:
        await self.session.execute(text(
            """UPDATE ml_training_runs SET status = :status, feature_names = :feature_names, samples = :samples,
               positive_samples = :positive_samples, training_start_at = :start_at, training_end_at = :end_at,
               trained_at = now(), metrics = CAST(:metrics AS jsonb), hyperparameters = CAST(:hyperparameters AS jsonb),
               artifact_uri = :artifact_uri, error = :error WHERE id = :id"""
        ), {"id": run_id, "status": status, "feature_names": feature_names, "samples": samples,
            "positive_samples": positive_samples, "start_at": training_start_at, "end_at": training_end_at, "metrics": json.dumps(dict(metrics)),
            "hyperparameters": json.dumps(dict(hyperparameters)), "artifact_uri": artifact_uri, "error": error})
        await self.session.commit()

    async def persist_similarity_scores(self, run_id: str, scores: list[dict[str, Any]], calculated_at: datetime) -> None:
        for item in scores:
            await self.session.execute(text(
                """INSERT INTO ml_similarity_scores (id, training_run_id, coin_id, score, model_probability, leaf_agreement, calculated_at, created_at)
                   VALUES (:id, :run_id, :coin_id, :score, :probability, :agreement, :calculated_at, now())
                   ON CONFLICT (training_run_id, coin_id) DO UPDATE SET score = EXCLUDED.score,
                     model_probability = EXCLUDED.model_probability, leaf_agreement = EXCLUDED.leaf_agreement,
                     calculated_at = EXCLUDED.calculated_at"""
            ), {"id": f"mls_{uuid4().hex}", "run_id": run_id, "coin_id": item["coin_id"], "score": item["score"],
                "probability": item["probability"], "agreement": item["agreement"], "calculated_at": calculated_at})
        await self.session.commit()
