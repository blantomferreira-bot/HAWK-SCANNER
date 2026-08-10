import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScannerSettings:
    scheduler_token: str
    alert_threshold: float
    model_version: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    discord_webhook_url: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from: str | None
    alert_email_to: tuple[str, ...]
    ml_artifact_dir: str
    require_all_data_sources: bool
    source_api_keys: dict[str, str]
    coingecko_catalog_pages: int
    catalog_refresh_seconds: int
    min_target_market_cap_usd: float
    max_target_market_cap_usd: float

    @classmethod
    def from_environment(cls) -> "ScannerSettings":
        recipients = tuple(item.strip() for item in os.getenv("ALERT_EMAIL_TO", "").split(",") if item.strip())
        threshold = float(os.getenv("HAWK_ALERT_THRESHOLD", "85"))
        if not 0 <= threshold <= 100:
            raise ValueError("HAWK_ALERT_THRESHOLD must be between 0 and 100")
        # One 250-asset page is a reliable base universe on CoinGecko's public
        # quota.  Deployments may increase this when an authenticated key is set.
        catalog_pages = int(os.getenv("COINGECKO_CATALOG_PAGES", "3"))
        catalog_refresh_seconds = int(os.getenv("CATALOG_REFRESH_SECONDS", "86400"))
        min_market_cap = float(os.getenv("MIN_TARGET_MARKET_CAP_USD", "30000000"))
        max_market_cap = float(os.getenv("MAX_TARGET_MARKET_CAP_USD", "100000000"))
        if catalog_pages < 1 or catalog_pages > 40:
            raise ValueError("COINGECKO_CATALOG_PAGES must be between 1 and 40")
        if catalog_refresh_seconds < 3600:
            raise ValueError("CATALOG_REFRESH_SECONDS must be at least 3600")
        if min_market_cap < 0 or max_market_cap <= min_market_cap:
            raise ValueError("MAX_TARGET_MARKET_CAP_USD must be greater than MIN_TARGET_MARKET_CAP_USD")
        return cls(
            scheduler_token=os.getenv("INTERNAL_SCHEDULER_TOKEN", ""),
            alert_threshold=threshold,
            model_version=os.getenv("HAWK_MODEL_VERSION", "hawk-score-v1"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
            smtp_host=os.getenv("SMTP_HOST") or None,
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME") or None,
            smtp_password=os.getenv("SMTP_PASSWORD") or None,
            smtp_from=os.getenv("SMTP_FROM") or None,
            alert_email_to=recipients,
            ml_artifact_dir=os.getenv("ML_ARTIFACT_DIR", "/var/lib/hawk-models"),
            # Public sources are sufficient for an operational base scanner.
            # Optional providers remain audited, but missing private keys never stop a scan.
            require_all_data_sources=os.getenv("REQUIRE_ALL_DATA_SOURCES", "false").lower() == "true",
            coingecko_catalog_pages=catalog_pages,
            catalog_refresh_seconds=catalog_refresh_seconds,
            min_target_market_cap_usd=min_market_cap,
            max_target_market_cap_usd=max_market_cap,
            source_api_keys={
                "coingecko": os.getenv("COINGECKO_API_KEY", ""), "coinglass": os.getenv("COINGLASS_API_KEY", ""),
                "defillama": os.getenv("DEFILLAMA_API_KEY", ""), "bitquery": os.getenv("BITQUERY_API_KEY", ""),
                "covalent": os.getenv("COVALENT_API_KEY", ""), "alchemy": os.getenv("ALCHEMY_API_KEY", ""),
                "moralis": os.getenv("MORALIS_API_KEY", ""), "etherscan": os.getenv("ETHERSCAN_API_KEY", ""),
                "bscscan": os.getenv("BSCSCAN_API_KEY", ""), "arbiscan": os.getenv("ARBISCAN_API_KEY", ""),
                "basescan": os.getenv("BASESCAN_API_KEY", ""), "solscan": os.getenv("SOLSCAN_API_KEY", ""),
            },
        )
