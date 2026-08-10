from hawk_worker.config import ScannerSettings


def test_scanner_settings_reject_invalid_catalog_pages(monkeypatch):
    monkeypatch.setenv("COINGECKO_CATALOG_PAGES", "0")
    monkeypatch.setenv("CATALOG_REFRESH_SECONDS", "86400")

    try:
        ScannerSettings.from_environment()
    except ValueError as error:
        assert "COINGECKO_CATALOG_PAGES" in str(error)
    else:
        raise AssertionError("invalid catalog page count was accepted")


def test_scanner_settings_allows_public_data_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_ALL_DATA_SOURCES", raising=False)
    monkeypatch.delenv("COINGECKO_CATALOG_PAGES", raising=False)
    monkeypatch.setenv("CATALOG_REFRESH_SECONDS", "3600")

    settings = ScannerSettings.from_environment()
    assert settings.require_all_data_sources is False
    assert settings.coingecko_catalog_pages == 1
