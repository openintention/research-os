from __future__ import annotations

import json

from clients.tiny_loop.api import HttpResearchOSApi
from research_os.http import OPENINTENTION_AGENT_USER_AGENT
from research_os.http import build_request


def test_build_request_sets_openintention_agent_user_agent() -> None:
    request = build_request("https://example.com/api/v1/efforts")
    assert request.get_header("User-agent") == OPENINTENTION_AGENT_USER_AGENT


def test_http_research_os_api_uses_explicit_agent_user_agent(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def read(self) -> bytes:
            return json.dumps([]).encode("utf-8")

    def fake_urlopen(request, timeout: float):  # type: ignore[no-redef,no-untyped-def]
        captured["user_agent"] = request.get_header("User-agent")
        return FakeResponse()

    monkeypatch.setattr("clients.tiny_loop.api.request.urlopen", fake_urlopen)

    api = HttpResearchOSApi("https://api.openintention.io")
    assert api.list_efforts() == []
    assert captured["user_agent"] == OPENINTENTION_AGENT_USER_AGENT
