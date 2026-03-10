from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request


class ResearchOSApi(Protocol):
    def list_efforts(self) -> list[dict[str, Any]]: ...

    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def append_event(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def recommend_next(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def get_workspace_discussion(self, workspace_id: str) -> dict[str, Any]: ...

    def get_snapshot_pull_request(self, workspace_id: str, snapshot_id: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class HttpResearchOSApi:
    base_url: str
    timeout_seconds: float = 30.0

    def list_efforts(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/efforts")

    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/workspaces", payload)

    def append_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/events", payload)

    def recommend_next(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/planner/recommend", payload)

    def get_workspace_discussion(self, workspace_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/publications/workspaces/{workspace_id}/discussion")

    def get_snapshot_pull_request(self, workspace_id: str, snapshot_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/v1/publications/workspaces/{workspace_id}/pull-requests/{snapshot_id}",
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        body = None
        headers = {"accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"
        req = request.Request(
            url=f"{self.base_url.rstrip('/')}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"{method} {path} failed with {exc.code}: {detail}") from exc
