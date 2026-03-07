"""Testing utilities — MockTransport for unit tests without a Docker daemon."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


class MockTransport:
    """A mock transport that replays registered fixture responses.

    Usage::

        transport = MockTransport()
        transport.register("GET", "/containers/json", [{"Id": "abc", ...}])

        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], Any] = {}
        self._stream_responses: dict[tuple[str, str], list[bytes]] = {}
        self._calls: list[tuple[str, str, dict[str, Any]]] = []

    def register(self, method: str, path: str, response: Any) -> None:
        """Register a response for a given method + path."""
        self._responses[(method.upper(), path)] = response

    def register_stream(self, method: str, path: str, chunks: list[bytes]) -> None:
        """Register stream chunks for a given method + path."""
        self._stream_responses[(method.upper(), path)] = chunks

    @property
    def calls(self) -> list[tuple[str, str, dict[str, Any]]]:
        """List of (method, path, params) calls made."""
        return self._calls

    def _find_response(self, method: str, path: str) -> Any:
        # Try exact match first
        key = (method.upper(), path)
        if key in self._responses:
            return self._responses[key]
        # Try prefix match (for versioned paths)
        for (m, p), resp in self._responses.items():
            if m == method.upper() and path.endswith(p):
                return resp
        return {}

    async def get(self, path: str, **params: Any) -> Any:
        self._calls.append(("GET", path, params))
        return self._find_response("GET", path)

    async def post(self, path: str, body: dict[str, Any] | None = None, **params: Any) -> Any:
        self._calls.append(("POST", path, params))
        return self._find_response("POST", path)

    async def post_raw(self, path: str, data: Any = None, headers: dict[str, str] | None = None, **params: Any) -> Any:
        self._calls.append(("POST", path, params))
        return self._find_response("POST", path)

    async def delete(self, path: str, **params: Any) -> None:
        self._calls.append(("DELETE", path, params))

    async def stream(self, method: str, path: str, **params: Any) -> AsyncIterator[bytes]:
        self._calls.append((method.upper(), path, params))
        key = (method.upper(), path)
        chunks = self._stream_responses.get(key, [])
        for chunk in chunks:
            yield chunk

    async def aclose(self) -> None:
        pass
