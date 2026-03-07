"""AsyncDockerClient — top-level entry point for aiowhales."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from .api.compose import ComposeAPI
from .api.containers import ContainersAPI
from .api.exec import ExecAPI
from .api.images import ImagesAPI
from .api.networks import NetworksAPI
from .api.volumes import VolumesAPI
from .models.events import DockerEvent, _parse_event
from .stream import json_stream
from .transport import TCPTransport, UnixSocketTransport


class AsyncDockerClient:
    """Async Docker client — owns transport lifetime and exposes all API namespaces.

    Usage::

        async with AsyncDockerClient() as docker:
            containers = await docker.containers.list()
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        transport: Any = None,
    ) -> None:
        if transport is not None:
            self._transport = transport
        elif url is not None:
            if url.startswith("tcp://") or url.startswith("https://"):
                self._transport = TCPTransport(url.replace("tcp://", "http://"))
            else:
                self._transport = UnixSocketTransport(url)
        else:
            self._transport = UnixSocketTransport()

        self.containers = ContainersAPI(self._transport)
        self.images = ImagesAPI(self._transport)
        self.volumes = VolumesAPI(self._transport)
        self.networks = NetworksAPI(self._transport)
        self.exec = ExecAPI(self._transport)
        self.compose = ComposeAPI()

    async def __aenter__(self) -> AsyncDockerClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying transport."""
        await self._transport.aclose()

    async def events(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[DockerEvent]:
        """Stream Docker engine events."""
        import json as _json

        params: dict[str, Any] = {}
        if since is not None:
            params["since"] = str(int(since.timestamp()))
        if until is not None:
            params["until"] = str(int(until.timestamp()))
        if filters is not None:
            params["filters"] = _json.dumps(filters)

        raw = self._transport.stream("GET", "/events", **params)
        async for data in json_stream(raw):
            yield _parse_event(data)


def from_env() -> AsyncDockerClient:
    """Create a client from environment variables.

    Reads DOCKER_HOST (defaults to unix:///var/run/docker.sock).
    """
    host = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
    if host.startswith("unix://"):
        socket_path = host[len("unix://"):]
        return AsyncDockerClient(socket_path)
    return AsyncDockerClient(host)
