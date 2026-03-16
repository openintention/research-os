from __future__ import annotations

import json

from clients.tiny_loop.api import HttpResearchOSApi
from research_os.http import OPENINTENTION_AGENT_USER_AGENT
from research_os.http import build_request
from research_os.http import open_url


def test_build_request_sets_openintention_agent_user_agent() -> None:
    request = build_request("https://example.com/api/v1/efforts")
    assert request.get_header("User-agent") == OPENINTENTION_AGENT_USER_AGENT


def test_open_url_uses_explicit_tls_context_for_https(monkeypatch) -> None:
    captured: dict[str, str | None] = {}
    sentinel_context = object()

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def read(self) -> bytes:
            return json.dumps([]).encode("utf-8")

    def fake_urlopen(request, timeout: float, context=None):  # type: ignore[no-redef,no-untyped-def]
        captured["user_agent"] = request.get_header("User-agent")
        captured["context"] = context
        return FakeResponse()

    monkeypatch.setattr("research_os.http._tls_context", lambda: sentinel_context)
    monkeypatch.setattr("research_os.http.urlopen", fake_urlopen)

    request = build_request("https://api.openintention.io/api/v1/efforts")
    with open_url(request, timeout=20) as response:
        assert json.loads(response.read().decode("utf-8")) == []
    assert captured["user_agent"] == OPENINTENTION_AGENT_USER_AGENT
    assert captured["context"] is sentinel_context


def test_open_url_skips_tls_context_for_http(monkeypatch) -> None:
    captured: dict[str, object | None] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def read(self) -> bytes:
            return b"ok"

    def fake_urlopen(request, timeout: float, context=None):  # type: ignore[no-redef,no-untyped-def]
        captured["context"] = context
        return FakeResponse()

    monkeypatch.setattr("research_os.http.urlopen", fake_urlopen)

    request = build_request("http://127.0.0.1:8000/healthz")
    with open_url(request, timeout=5) as response:
        assert response.read() == b"ok"

    assert captured["context"] is None


def test_http_research_os_api_uses_explicit_agent_user_agent(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def read(self) -> bytes:
            return json.dumps([]).encode("utf-8")

    def fake_open_url(request, *, timeout: float):  # type: ignore[no-untyped-def]
        captured["user_agent"] = request.get_header("User-agent")
        assert timeout == 30.0
        return FakeResponse()

    monkeypatch.setattr("clients.tiny_loop.api.open_url", fake_open_url)

    api = HttpResearchOSApi("https://api.openintention.io")
    assert api.list_efforts() == []
    assert captured["user_agent"] == OPENINTENTION_AGENT_USER_AGENT
