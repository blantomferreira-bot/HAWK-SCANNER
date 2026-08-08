import os


def scan_interval_minutes() -> int:
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "10"))
    if interval != 10:
        raise ValueError("SCAN_INTERVAL_MINUTES must remain 10 for the configured scanner cadence")
    return interval


def daily_learning_hour_utc() -> int:
    hour = int(os.getenv("ML_TRAIN_HOUR_UTC", "0"))
    if not 0 <= hour <= 23:
        raise ValueError("ML_TRAIN_HOUR_UTC must be between 0 and 23")
    return hour
