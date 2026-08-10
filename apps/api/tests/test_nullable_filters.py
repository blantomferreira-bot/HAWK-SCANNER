from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]


def test_nullable_market_filters_have_explicit_postgres_types() -> None:
    source = (API_ROOT / "src" / "presentation" / "api" / "v1" / "market.py").read_text(encoding="utf-8")

    # asyncpg cannot infer a type for a NULL bind used only in `:value IS NULL`.
    assert "CAST(:model_version AS text) IS NULL" in source
    assert "CAST(:direction AS text) IS NULL" in source
    assert "CAST(:start_at AS timestamptz) IS NULL" in source
    assert "CAST(:end_at AS timestamptz) IS NULL" in source
    assert ":model_version IS NULL" not in source


def test_nullable_alert_filter_has_explicit_postgres_type() -> None:
    source = (API_ROOT / "src" / "presentation" / "api" / "v1" / "user_data.py").read_text(encoding="utf-8")

    assert "CAST(:status AS text) IS NULL" in source
