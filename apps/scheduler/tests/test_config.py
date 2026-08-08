from hawk_scheduler.config import daily_learning_hour_utc, scan_interval_minutes


def test_scheduler_requires_ten_minute_scan_interval(monkeypatch):
    monkeypatch.setenv("SCAN_INTERVAL_MINUTES", "5")

    try:
        scan_interval_minutes()
    except ValueError as error:
        assert "remain 10" in str(error)
    else:
        raise AssertionError("non-compliant scan interval was accepted")


def test_scheduler_accepts_utc_hour(monkeypatch):
    monkeypatch.setenv("ML_TRAIN_HOUR_UTC", "23")
    assert daily_learning_hour_utc() == 23
