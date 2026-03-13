from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.request import Request
from urllib.request import urlopen

OPENINTENTION_AGENT_USER_AGENT = (
    "OpenIntentionAgent/0.1 (+https://github.com/openintention/research-os)"
)


def build_request(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
) -> Request:
    request_headers = {"User-Agent": OPENINTENTION_AGENT_USER_AGENT}
    if headers:
        request_headers.update(dict(headers))
    return Request(url=url, data=data, headers=request_headers, method=method)


def read_json(url: str, *, timeout: float = 20.0, headers: Mapping[str, str] | None = None) -> Any:
    request = build_request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
