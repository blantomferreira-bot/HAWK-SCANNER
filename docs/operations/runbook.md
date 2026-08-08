# HAWK SCANNER operational runbook

## First deployment

1. Create `.env` from the root template and use a secret manager in managed environments.
2. Set provider credentials and notification destinations.
3. Run `docker compose up --build` and wait for `migrate` to finish successfully.
4. Confirm `GET /health/ready` for API and worker.
5. Register the account matching `BOOTSTRAP_ADMIN_EMAIL`, then remove that configuration value and restart the API.
6. Create plans with `POST /api/v1/admin/plans`; grant a test subscription with `POST /api/v1/admin/subscriptions`.
7. Inspect the first scanner run in `scanner_runs` and source consultations in `logs`.

## Expected lifecycle

The scheduler triggers the worker immediately, then every 10 minutes. The worker holds a Redis lock for the maximum scan duration, records a scanner run, checks providers, refreshes its asset catalog when its daily cache expires, persists snapshots, calibrates the score and writes ranking/history/alerts atomically by stage.

The daily ML trigger calls the worker at `ML_TRAIN_HOUR_UTC`. It labels historic windows only after the required future price horizon exists. Until enough positive and negative samples exist, the run is stored as `WARMING_UP` rather than producing a misleading model.

## Incident handling

- If an API health endpoint is live but not ready, inspect PostgreSQL and Redis containers first.
- If a scan fails in strict mode, inspect `logs` rows where `event = 'source_consultation'`; correct credentials, provider entitlement or outbound connectivity before retrying.
- Do not lower the score threshold to test notifications in production. Use a separate test recipient and a controlled staging database.
- Preserve `scanner_runs`, `scores`, `score_history`, `ml_training_runs` and `ml_similarity_scores` in database backups; they form the auditable decision lineage.
