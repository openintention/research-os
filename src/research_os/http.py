from __future__ import annotations

from functools import lru_cache
import json
import ssl
from typing import Any, Mapping
from urllib.parse import urlparse
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


def open_url(request: Request, *, timeout: float):
    context = _tls_context() if _uses_https(request.full_url) else None
    if context is None:
        return urlopen(request, timeout=timeout)
    return urlopen(request, timeout=timeout, context=context)


def read_json(url: str, *, timeout: float = 20.0, headers: Mapping[str, str] | None = None) -> Any:
    request = build_request(url, headers=headers)
    with open_url(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_text(url: str, *, timeout: float = 20.0, headers: Mapping[str, str] | None = None) -> str:
    request = build_request(url, headers=headers)
    with open_url(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _uses_https(url: str) -> bool:
    return urlparse(url).scheme.lower() == "https"


@lru_cache(maxsize=1)
def _tls_context() -> ssl.SSLContext:
    import certifi

    return ssl.create_default_context(cafile=certifi.where())
