-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('USER', 'ANALYST', 'ADMIN', 'SUPER_ADMIN');

-- CreateEnum
CREATE TYPE "UserStatus" AS ENUM ('PENDING', 'ACTIVE', 'SUSPENDED', 'DELETED');

-- CreateEnum
CREATE TYPE "BillingInterval" AS ENUM ('MONTH', 'YEAR');

-- CreateEnum
CREATE TYPE "SubscriptionStatus" AS ENUM ('TRIALING', 'ACTIVE', 'PAST_DUE', 'PAUSED', 'CANCELED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "AssetType" AS ENUM ('CRYPTOCURRENCY', 'STABLECOIN', 'TOKEN', 'DERIVATIVE');

-- CreateEnum
CREATE TYPE "MarketType" AS ENUM ('SPOT', 'PERPETUAL', 'FUTURE', 'OPTION');

-- CreateEnum
CREATE TYPE "MetricType" AS ENUM ('PRICE', 'VOLUME', 'MARKET_CAP', 'LIQUIDITY', 'VOLATILITY', 'SPREAD', 'DEPTH', 'TVL', 'TRANSACTION_COUNT', 'ACTIVE_ADDRESSES', 'CUSTOM');

-- CreateEnum
CREATE TYPE "MetricInterval" AS ENUM ('ONE_MINUTE', 'FIVE_MINUTES', 'TEN_MINUTES', 'FIFTEEN_MINUTES', 'ONE_HOUR', 'FOUR_HOURS', 'ONE_DAY');

-- CreateEnum
CREATE TYPE "ChainNetwork" AS ENUM ('BITCOIN', 'ETHEREUM', 'SOLANA', 'BNB_CHAIN', 'ARBITRUM', 'BASE', 'POLYGON', 'AVALANCHE', 'OPTIMISM', 'OTHER');

-- CreateEnum
CREATE TYPE "TransferType" AS ENUM ('DEPOSIT', 'WITHDRAWAL', 'INTERNAL', 'ON_CHAIN');

-- CreateEnum
CREATE TYPE "ScoreDirection" AS ENUM ('BULLISH', 'BEARISH', 'NEUTRAL');

-- CreateEnum
CREATE TYPE "AlertType" AS ENUM ('SCORE_THRESHOLD', 'SCORE_CHANGE', 'PRICE_CHANGE', 'VOLUME_SPIKE', 'FUNDING_EXTREME', 'OPEN_INTEREST_CHANGE', 'LIQUIDATION_SPIKE', 'WHALE_TRANSFER');

-- CreateEnum
CREATE TYPE "AlertChannel" AS ENUM ('IN_APP', 'EMAIL', 'TELEGRAM', 'DISCORD', 'WEBHOOK');

-- CreateEnum
CREATE TYPE "AlertStatus" AS ENUM ('ACTIVE', 'PAUSED', 'ARCHIVED');

-- CreateEnum
CREATE TYPE "AlertEventStatus" AS ENUM ('PENDING', 'DELIVERED', 'FAILED', 'SUPPRESSED');

-- CreateEnum
CREATE TYPE "LogLevel" AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');

-- CreateEnum
CREATE TYPE "ApiKeyStatus" AS ENUM ('ACTIVE', 'REVOKED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "ScannerRunStatus" AS ENUM ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED');

-- CreateEnum
CREATE TYPE "DeliveryStatus" AS ENUM ('PENDING', 'DELIVERED', 'FAILED', 'SKIPPED');

-- CreateEnum
CREATE TYPE "MlTrainingStatus" AS ENUM ('RUNNING', 'COMPLETED', 'WARMING_UP', 'FAILED');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" VARCHAR(320) NOT NULL,
    "password_hash" TEXT NOT NULL,
    "display_name" TEXT,
    "role" "UserRole" NOT NULL DEFAULT 'USER',
    "status" "UserStatus" NOT NULL DEFAULT 'PENDING',
    "email_verified_at" TIMESTAMPTZ(6),
    "last_login_at" TIMESTAMPTZ(6),
    "timezone" TEXT NOT NULL DEFAULT 'UTC',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,
    "deleted_at" TIMESTAMPTZ(6),

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "plans" (
    "id" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "billing_interval" "BillingInterval" NOT NULL,
    "price_cents" INTEGER NOT NULL,
    "currency" CHAR(3) NOT NULL DEFAULT 'USD',
    "trial_days" INTEGER NOT NULL DEFAULT 0,
    "max_watchlists" INTEGER NOT NULL DEFAULT 1,
    "max_alerts" INTEGER NOT NULL DEFAULT 3,
    "max_api_keys" INTEGER NOT NULL DEFAULT 0,
    "entitlements" JSONB NOT NULL DEFAULT '{}',
    "provider_product_id" TEXT,
    "provider_price_id" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "plans_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subscriptions" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "plan_id" TEXT NOT NULL,
    "status" "SubscriptionStatus" NOT NULL DEFAULT 'TRIALING',
    "provider_customer_id" TEXT,
    "provider_subscription_id" TEXT,
    "current_period_start" TIMESTAMPTZ(6) NOT NULL,
    "current_period_end" TIMESTAMPTZ(6) NOT NULL,
    "cancel_at_period_end" BOOLEAN NOT NULL DEFAULT false,
    "canceled_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "subscriptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "coins" (
    "id" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT,
    "asset_type" "AssetType" NOT NULL DEFAULT 'CRYPTOCURRENCY',
    "contract_address" TEXT,
    "network" "ChainNetwork",
    "decimals" INTEGER,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "coins_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "exchanges" (
    "id" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "website_url" TEXT,
    "api_base_url" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "rate_limit_rpm" INTEGER,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "exchanges_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "markets" (
    "id" TEXT NOT NULL,
    "exchange_id" TEXT NOT NULL,
    "base_coin_id" TEXT NOT NULL,
    "quote_coin_id" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "market_type" "MarketType" NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "markets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "metrics" (
    "id" BIGSERIAL NOT NULL,
    "coin_id" TEXT NOT NULL,
    "market_id" TEXT,
    "type" "MetricType" NOT NULL,
    "interval" "MetricInterval" NOT NULL,
    "value" DECIMAL(38,18) NOT NULL,
    "source" TEXT NOT NULL,
    "observed_at" TIMESTAMPTZ(6) NOT NULL,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "metrics_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "funding" (
    "id" BIGSERIAL NOT NULL,
    "market_id" TEXT NOT NULL,
    "rate" DECIMAL(20,12) NOT NULL,
    "mark_price" DECIMAL(38,18),
    "next_funding_at" TIMESTAMPTZ(6),
    "source" TEXT NOT NULL,
    "observed_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "funding_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "open_interest" (
    "id" BIGSERIAL NOT NULL,
    "market_id" TEXT NOT NULL,
    "value" DECIMAL(38,18) NOT NULL,
    "value_usd" DECIMAL(38,18),
    "source" TEXT NOT NULL,
    "observed_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "open_interest_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "liquidations" (
    "id" TEXT NOT NULL,
    "market_id" TEXT,
    "exchange_id" TEXT,
    "side" TEXT NOT NULL,
    "price" DECIMAL(38,18),
    "quantity" DECIMAL(38,18),
    "value_usd" DECIMAL(38,18),
    "source_event_id" TEXT,
    "source" TEXT NOT NULL,
    "liquidated_at" TIMESTAMPTZ(6) NOT NULL,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "liquidations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "wallets" (
    "id" TEXT NOT NULL,
    "address" TEXT NOT NULL,
    "network" "ChainNetwork" NOT NULL,
    "coin_id" TEXT,
    "label" TEXT,
    "entity_name" TEXT,
    "is_exchange" BOOLEAN NOT NULL DEFAULT false,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "first_seen_at" TIMESTAMPTZ(6),
    "last_seen_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "wallets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "whales" (
    "id" TEXT NOT NULL,
    "wallet_id" TEXT NOT NULL,
    "classification" TEXT NOT NULL DEFAULT 'UNKNOWN',
    "confidence" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "estimated_value_usd" DECIMAL(38,18),
    "tags" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "last_evaluated_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "whales_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "transfers" (
    "id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "from_wallet_id" TEXT,
    "to_wallet_id" TEXT,
    "exchange_id" TEXT,
    "network" "ChainNetwork" NOT NULL,
    "type" "TransferType" NOT NULL,
    "transaction_hash" TEXT,
    "amount" DECIMAL(38,18) NOT NULL,
    "value_usd" DECIMAL(38,18),
    "occurred_at" TIMESTAMPTZ(6) NOT NULL,
    "source" TEXT NOT NULL,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "transfers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scores" (
    "id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "market_id" TEXT,
    "model_version" TEXT NOT NULL,
    "value" DECIMAL(6,3) NOT NULL,
    "confidence" DECIMAL(5,4) NOT NULL,
    "direction" "ScoreDirection" NOT NULL DEFAULT 'NEUTRAL',
    "factors" JSONB NOT NULL DEFAULT '{}',
    "calculated_at" TIMESTAMPTZ(6) NOT NULL,
    "expires_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "scores_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "score_history" (
    "id" BIGSERIAL NOT NULL,
    "coin_id" TEXT NOT NULL,
    "market_id" TEXT,
    "model_version" TEXT NOT NULL,
    "value" DECIMAL(6,3) NOT NULL,
    "confidence" DECIMAL(5,4) NOT NULL,
    "direction" "ScoreDirection" NOT NULL DEFAULT 'NEUTRAL',
    "factors" JSONB NOT NULL DEFAULT '{}',
    "calculated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "score_history_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "history" (
    "id" BIGSERIAL NOT NULL,
    "coin_id" TEXT NOT NULL,
    "market_id" TEXT,
    "interval" "MetricInterval" NOT NULL,
    "open" DECIMAL(38,18) NOT NULL,
    "high" DECIMAL(38,18) NOT NULL,
    "low" DECIMAL(38,18) NOT NULL,
    "close" DECIMAL(38,18) NOT NULL,
    "volume" DECIMAL(38,18),
    "quote_volume" DECIMAL(38,18),
    "source" TEXT NOT NULL,
    "opened_at" TIMESTAMPTZ(6) NOT NULL,
    "closed_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "history_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "watchlists" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "is_default" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "watchlists_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "watchlist_items" (
    "id" TEXT NOT NULL,
    "watchlist_id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "note" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "watchlist_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alerts" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "coin_id" TEXT,
    "type" "AlertType" NOT NULL,
    "channel" "AlertChannel" NOT NULL,
    "status" "AlertStatus" NOT NULL DEFAULT 'ACTIVE',
    "name" TEXT NOT NULL,
    "conditions" JSONB NOT NULL,
    "destination" TEXT,
    "cooldown_secs" INTEGER NOT NULL DEFAULT 900,
    "last_triggered_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "alerts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alert_events" (
    "id" TEXT NOT NULL,
    "alert_id" TEXT NOT NULL,
    "status" "AlertEventStatus" NOT NULL DEFAULT 'PENDING',
    "payload" JSONB NOT NULL,
    "error" TEXT,
    "triggered_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "delivered_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "alert_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "logs" (
    "id" BIGSERIAL NOT NULL,
    "user_id" TEXT,
    "level" "LogLevel" NOT NULL,
    "service" TEXT NOT NULL,
    "event" TEXT NOT NULL,
    "request_id" TEXT,
    "trace_id" TEXT,
    "job_id" TEXT,
    "message" TEXT NOT NULL,
    "context" JSONB NOT NULL DEFAULT '{}',
    "occurred_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "api_keys" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "prefix" TEXT NOT NULL,
    "secret_hash" TEXT NOT NULL,
    "scopes" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "status" "ApiKeyStatus" NOT NULL DEFAULT 'ACTIVE',
    "last_used_at" TIMESTAMPTZ(6),
    "expires_at" TIMESTAMPTZ(6),
    "revoked_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "api_keys_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scanner_runs" (
    "id" TEXT NOT NULL,
    "status" "ScannerRunStatus" NOT NULL DEFAULT 'RUNNING',
    "started_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMPTZ(6),
    "coins_seen" INTEGER NOT NULL DEFAULT 0,
    "scores_saved" INTEGER NOT NULL DEFAULT 0,
    "alerts_made" INTEGER NOT NULL DEFAULT 0,
    "error" TEXT,
    "metadata" JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT "scanner_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scanner_alerts" (
    "id" TEXT NOT NULL,
    "scanner_run_id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "score_id" TEXT NOT NULL,
    "score_value" DECIMAL(6,3) NOT NULL,
    "threshold" DECIMAL(6,3) NOT NULL,
    "status" "DeliveryStatus" NOT NULL DEFAULT 'PENDING',
    "payload" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "scanner_alerts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scanner_alert_deliveries" (
    "id" TEXT NOT NULL,
    "scanner_alert_id" TEXT NOT NULL,
    "channel" "AlertChannel" NOT NULL,
    "destination" TEXT NOT NULL,
    "status" "DeliveryStatus" NOT NULL DEFAULT 'PENDING',
    "error" TEXT,
    "attempted_at" TIMESTAMPTZ(6),
    "delivered_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "scanner_alert_deliveries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ml_feature_snapshots" (
    "id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "observed_at" TIMESTAMPTZ(6) NOT NULL,
    "window_start_at" TIMESTAMPTZ(6) NOT NULL,
    "window_days" INTEGER NOT NULL,
    "reference_price" DECIMAL(38,18),
    "features" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ml_feature_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ml_training_runs" (
    "id" TEXT NOT NULL,
    "status" "MlTrainingStatus" NOT NULL DEFAULT 'RUNNING',
    "model_type" TEXT NOT NULL,
    "label_definition" TEXT NOT NULL,
    "window_days" INTEGER NOT NULL,
    "feature_names" TEXT[],
    "training_start_at" TIMESTAMPTZ(6),
    "training_end_at" TIMESTAMPTZ(6),
    "trained_at" TIMESTAMPTZ(6),
    "samples" INTEGER NOT NULL DEFAULT 0,
    "positive_samples" INTEGER NOT NULL DEFAULT 0,
    "metrics" JSONB NOT NULL DEFAULT '{}',
    "hyperparameters" JSONB NOT NULL DEFAULT '{}',
    "artifact_uri" TEXT,
    "error" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ml_training_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ml_similarity_scores" (
    "id" TEXT NOT NULL,
    "training_run_id" TEXT NOT NULL,
    "coin_id" TEXT NOT NULL,
    "score" DECIMAL(6,3) NOT NULL,
    "model_probability" DECIMAL(10,8) NOT NULL,
    "leaf_agreement" DECIMAL(10,8) NOT NULL,
    "calculated_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ml_similarity_scores_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_status_idx" ON "users"("status");

-- CreateIndex
CREATE INDEX "users_role_status_idx" ON "users"("role", "status");

-- CreateIndex
CREATE UNIQUE INDEX "plans_code_key" ON "plans"("code");

-- CreateIndex
CREATE UNIQUE INDEX "plans_provider_product_id_key" ON "plans"("provider_product_id");

-- CreateIndex
CREATE UNIQUE INDEX "plans_provider_price_id_key" ON "plans"("provider_price_id");

-- CreateIndex
CREATE INDEX "plans_is_active_billing_interval_idx" ON "plans"("is_active", "billing_interval");

-- CreateIndex
CREATE UNIQUE INDEX "subscriptions_provider_subscription_id_key" ON "subscriptions"("provider_subscription_id");

-- CreateIndex
CREATE INDEX "subscriptions_user_id_status_idx" ON "subscriptions"("user_id", "status");

-- CreateIndex
CREATE INDEX "subscriptions_status_current_period_end_idx" ON "subscriptions"("status", "current_period_end");

-- CreateIndex
CREATE UNIQUE INDEX "coins_slug_key" ON "coins"("slug");

-- CreateIndex
CREATE INDEX "coins_symbol_idx" ON "coins"("symbol");

-- CreateIndex
CREATE INDEX "coins_is_active_asset_type_idx" ON "coins"("is_active", "asset_type");

-- CreateIndex
CREATE UNIQUE INDEX "coins_symbol_network_contract_address_key" ON "coins"("symbol", "network", "contract_address");

-- CreateIndex
CREATE UNIQUE INDEX "exchanges_code_key" ON "exchanges"("code");

-- CreateIndex
CREATE INDEX "exchanges_is_active_idx" ON "exchanges"("is_active");

-- CreateIndex
CREATE INDEX "markets_base_coin_id_market_type_is_active_idx" ON "markets"("base_coin_id", "market_type", "is_active");

-- CreateIndex
CREATE INDEX "markets_exchange_id_is_active_idx" ON "markets"("exchange_id", "is_active");

-- CreateIndex
CREATE UNIQUE INDEX "markets_exchange_id_symbol_market_type_key" ON "markets"("exchange_id", "symbol", "market_type");

-- CreateIndex
CREATE INDEX "metrics_coin_id_type_interval_observed_at_idx" ON "metrics"("coin_id", "type", "interval", "observed_at" DESC);

-- CreateIndex
CREATE INDEX "metrics_market_id_type_observed_at_idx" ON "metrics"("market_id", "type", "observed_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "metrics_coin_id_market_id_type_interval_source_observed_at_key" ON "metrics"("coin_id", "market_id", "type", "interval", "source", "observed_at");

-- CreateIndex
CREATE INDEX "funding_market_id_observed_at_idx" ON "funding"("market_id", "observed_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "funding_market_id_source_observed_at_key" ON "funding"("market_id", "source", "observed_at");

-- CreateIndex
CREATE INDEX "open_interest_market_id_observed_at_idx" ON "open_interest"("market_id", "observed_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "open_interest_market_id_source_observed_at_key" ON "open_interest"("market_id", "source", "observed_at");

-- CreateIndex
CREATE UNIQUE INDEX "liquidations_source_event_id_key" ON "liquidations"("source_event_id");

-- CreateIndex
CREATE INDEX "liquidations_market_id_liquidated_at_idx" ON "liquidations"("market_id", "liquidated_at" DESC);

-- CreateIndex
CREATE INDEX "liquidations_exchange_id_liquidated_at_idx" ON "liquidations"("exchange_id", "liquidated_at" DESC);

-- CreateIndex
CREATE INDEX "liquidations_liquidated_at_idx" ON "liquidations"("liquidated_at" DESC);

-- CreateIndex
CREATE INDEX "wallets_network_is_exchange_idx" ON "wallets"("network", "is_exchange");

-- CreateIndex
CREATE UNIQUE INDEX "wallets_address_network_key" ON "wallets"("address", "network");

-- CreateIndex
CREATE UNIQUE INDEX "whales_wallet_id_key" ON "whales"("wallet_id");

-- CreateIndex
CREATE INDEX "whales_classification_confidence_idx" ON "whales"("classification", "confidence");

-- CreateIndex
CREATE INDEX "transfers_coin_id_occurred_at_idx" ON "transfers"("coin_id", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "transfers_from_wallet_id_occurred_at_idx" ON "transfers"("from_wallet_id", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "transfers_to_wallet_id_occurred_at_idx" ON "transfers"("to_wallet_id", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "transfers_value_usd_occurred_at_idx" ON "transfers"("value_usd", "occurred_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "transfers_network_transaction_hash_key" ON "transfers"("network", "transaction_hash");

-- CreateIndex
CREATE INDEX "scores_value_confidence_calculated_at_idx" ON "scores"("value" DESC, "confidence" DESC, "calculated_at" DESC);

-- CreateIndex
CREATE INDEX "scores_coin_id_calculated_at_idx" ON "scores"("coin_id", "calculated_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "scores_coin_id_market_id_model_version_calculated_at_key" ON "scores"("coin_id", "market_id", "model_version", "calculated_at");

-- CreateIndex
CREATE INDEX "score_history_coin_id_model_version_calculated_at_idx" ON "score_history"("coin_id", "model_version", "calculated_at" DESC);

-- CreateIndex
CREATE INDEX "score_history_market_id_model_version_calculated_at_idx" ON "score_history"("market_id", "model_version", "calculated_at" DESC);

-- CreateIndex
CREATE INDEX "history_coin_id_interval_opened_at_idx" ON "history"("coin_id", "interval", "opened_at" DESC);

-- CreateIndex
CREATE INDEX "history_market_id_interval_opened_at_idx" ON "history"("market_id", "interval", "opened_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "history_coin_id_market_id_interval_source_opened_at_key" ON "history"("coin_id", "market_id", "interval", "source", "opened_at");

-- CreateIndex
CREATE INDEX "watchlists_user_id_is_default_idx" ON "watchlists"("user_id", "is_default");

-- CreateIndex
CREATE UNIQUE INDEX "watchlists_user_id_name_key" ON "watchlists"("user_id", "name");

-- CreateIndex
CREATE INDEX "watchlist_items_coin_id_idx" ON "watchlist_items"("coin_id");

-- CreateIndex
CREATE UNIQUE INDEX "watchlist_items_watchlist_id_coin_id_key" ON "watchlist_items"("watchlist_id", "coin_id");

-- CreateIndex
CREATE INDEX "alerts_user_id_status_idx" ON "alerts"("user_id", "status");

-- CreateIndex
CREATE INDEX "alerts_coin_id_type_status_idx" ON "alerts"("coin_id", "type", "status");

-- CreateIndex
CREATE INDEX "alert_events_alert_id_triggered_at_idx" ON "alert_events"("alert_id", "triggered_at" DESC);

-- CreateIndex
CREATE INDEX "alert_events_status_created_at_idx" ON "alert_events"("status", "created_at");

-- CreateIndex
CREATE INDEX "logs_level_occurred_at_idx" ON "logs"("level", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "logs_service_occurred_at_idx" ON "logs"("service", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "logs_request_id_idx" ON "logs"("request_id");

-- CreateIndex
CREATE INDEX "logs_user_id_occurred_at_idx" ON "logs"("user_id", "occurred_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "api_keys_prefix_key" ON "api_keys"("prefix");

-- CreateIndex
CREATE INDEX "api_keys_user_id_status_idx" ON "api_keys"("user_id", "status");

-- CreateIndex
CREATE INDEX "api_keys_status_expires_at_idx" ON "api_keys"("status", "expires_at");

-- CreateIndex
CREATE UNIQUE INDEX "api_keys_user_id_name_key" ON "api_keys"("user_id", "name");

-- CreateIndex
CREATE INDEX "scanner_runs_status_started_at_idx" ON "scanner_runs"("status", "started_at" DESC);

-- CreateIndex
CREATE INDEX "scanner_alerts_created_at_idx" ON "scanner_alerts"("created_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "scanner_alerts_coin_id_score_id_key" ON "scanner_alerts"("coin_id", "score_id");

-- CreateIndex
CREATE INDEX "scanner_alert_deliveries_status_created_at_idx" ON "scanner_alert_deliveries"("status", "created_at");

-- CreateIndex
CREATE UNIQUE INDEX "scanner_alert_deliveries_scanner_alert_id_channel_destinati_key" ON "scanner_alert_deliveries"("scanner_alert_id", "channel", "destination");

-- CreateIndex
CREATE INDEX "ml_feature_snapshots_observed_at_idx" ON "ml_feature_snapshots"("observed_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "ml_feature_snapshots_coin_id_observed_at_window_days_key" ON "ml_feature_snapshots"("coin_id", "observed_at", "window_days");

-- CreateIndex
CREATE INDEX "ml_training_runs_status_created_at_idx" ON "ml_training_runs"("status", "created_at" DESC);

-- CreateIndex
CREATE INDEX "ml_similarity_scores_score_calculated_at_idx" ON "ml_similarity_scores"("score" DESC, "calculated_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "ml_similarity_scores_training_run_id_coin_id_key" ON "ml_similarity_scores"("training_run_id", "coin_id");

-- AddForeignKey
ALTER TABLE "subscriptions" ADD CONSTRAINT "subscriptions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subscriptions" ADD CONSTRAINT "subscriptions_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "plans"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "markets" ADD CONSTRAINT "markets_exchange_id_fkey" FOREIGN KEY ("exchange_id") REFERENCES "exchanges"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "markets" ADD CONSTRAINT "markets_base_coin_id_fkey" FOREIGN KEY ("base_coin_id") REFERENCES "coins"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "markets" ADD CONSTRAINT "markets_quote_coin_id_fkey" FOREIGN KEY ("quote_coin_id") REFERENCES "coins"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "metrics" ADD CONSTRAINT "metrics_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "metrics" ADD CONSTRAINT "metrics_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "funding" ADD CONSTRAINT "funding_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "open_interest" ADD CONSTRAINT "open_interest_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "liquidations" ADD CONSTRAINT "liquidations_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "liquidations" ADD CONSTRAINT "liquidations_exchange_id_fkey" FOREIGN KEY ("exchange_id") REFERENCES "exchanges"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "wallets" ADD CONSTRAINT "wallets_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "whales" ADD CONSTRAINT "whales_wallet_id_fkey" FOREIGN KEY ("wallet_id") REFERENCES "wallets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transfers" ADD CONSTRAINT "transfers_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transfers" ADD CONSTRAINT "transfers_from_wallet_id_fkey" FOREIGN KEY ("from_wallet_id") REFERENCES "wallets"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transfers" ADD CONSTRAINT "transfers_to_wallet_id_fkey" FOREIGN KEY ("to_wallet_id") REFERENCES "wallets"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transfers" ADD CONSTRAINT "transfers_exchange_id_fkey" FOREIGN KEY ("exchange_id") REFERENCES "exchanges"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scores" ADD CONSTRAINT "scores_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scores" ADD CONSTRAINT "scores_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "score_history" ADD CONSTRAINT "score_history_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "score_history" ADD CONSTRAINT "score_history_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "history" ADD CONSTRAINT "history_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "history" ADD CONSTRAINT "history_market_id_fkey" FOREIGN KEY ("market_id") REFERENCES "markets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "watchlists" ADD CONSTRAINT "watchlists_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "watchlist_items" ADD CONSTRAINT "watchlist_items_watchlist_id_fkey" FOREIGN KEY ("watchlist_id") REFERENCES "watchlists"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "watchlist_items" ADD CONSTRAINT "watchlist_items_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alerts" ADD CONSTRAINT "alerts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alerts" ADD CONSTRAINT "alerts_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_events" ADD CONSTRAINT "alert_events_alert_id_fkey" FOREIGN KEY ("alert_id") REFERENCES "alerts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "logs" ADD CONSTRAINT "logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "api_keys" ADD CONSTRAINT "api_keys_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scanner_alerts" ADD CONSTRAINT "scanner_alerts_scanner_run_id_fkey" FOREIGN KEY ("scanner_run_id") REFERENCES "scanner_runs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scanner_alerts" ADD CONSTRAINT "scanner_alerts_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scanner_alerts" ADD CONSTRAINT "scanner_alerts_score_id_fkey" FOREIGN KEY ("score_id") REFERENCES "scores"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scanner_alert_deliveries" ADD CONSTRAINT "scanner_alert_deliveries_scanner_alert_id_fkey" FOREIGN KEY ("scanner_alert_id") REFERENCES "scanner_alerts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ml_feature_snapshots" ADD CONSTRAINT "ml_feature_snapshots_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ml_similarity_scores" ADD CONSTRAINT "ml_similarity_scores_training_run_id_fkey" FOREIGN KEY ("training_run_id") REFERENCES "ml_training_runs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ml_similarity_scores" ADD CONSTRAINT "ml_similarity_scores_coin_id_fkey" FOREIGN KEY ("coin_id") REFERENCES "coins"("id") ON DELETE CASCADE ON UPDATE CASCADE;
