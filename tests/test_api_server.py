from __future__ import annotations

from research_os.api_server import _port_from_env


def test_port_from_env_uses_runtime_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "9123")

    assert _port_from_env() == 9123


def test_port_from_env_falls_back_on_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "not-a-number")

    assert _port_from_env() == 8000
