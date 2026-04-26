import pytest
from pathlib import Path

import sportybet.client as client


def test_place_bet_with_code_requires_credentials(monkeypatch):
    monkeypatch.delenv("SPORTYBET_PHONE", raising=False)
    monkeypatch.delenv("SPORTYBET_PASSWORD", raising=False)

    success, message = client.place_bet_with_code("ABC123", 100)

    assert success is False
    assert "credentials" in message.lower()


def test_resolve_driver_executable_prefers_chromedriver(tmp_path):
    temp_dir = Path(tmp_path)
    third_party = temp_dir / "THIRD_PARTY_NOTICES.chromedriver"
    driver = temp_dir / "chromedriver"
    third_party.write_text("notice")
    driver.write_text("binary")

    resolved = client._resolve_driver_executable(str(third_party))

    assert resolved == str(driver)


def test_resolve_driver_executable_accepts_chromedriver_path(tmp_path):
    temp_dir = Path(tmp_path)
    driver = temp_dir / "chromedriver"
    driver.write_text("binary")

    resolved = client._resolve_driver_executable(str(driver))

    assert resolved == str(driver)


def test_enter_booking_code_requires_one_cut(monkeypatch):
    pytest.importorskip("selenium")

    class _FakeElement:
        def click(self):
            pass

        def is_selected(self):
            return False

        def get_attribute(self, name):
            return ""

    class _FakeWait:
        def until(self, condition):
            return _FakeElement()

    class _FakeDriver:
        def get(self, url):
            pass

        def execute_script(self, script, element):
            pass

    monkeypatch.setattr(client, "_enable_one_cut", lambda driver, wait: False)

    success, message = client._enter_booking_code(_FakeDriver(), _FakeWait(), "ABC123", None)

    assert success is False
    assert "one cut" in message.lower()
