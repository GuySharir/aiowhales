"""Container snapshot model."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..api.containers import ContainersAPI
    from .exec_result import ExecResult
    from ..stream import LogLine


@dataclass(frozen=True)
class ContainerStats:
    """Snapshot of container resource usage."""

    cpu_percent: float
    memory_mb: float
    memory_limit_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    pids: int
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class Container:
    """Immutable snapshot of a Docker container."""

    id: str
    name: str
    status: str
    image: str
    created: datetime
    labels: dict[str, str]
    ports: dict[str, list[Any]]
    env: dict[str, str]
    _api: ContainersAPI = field(repr=False)

    async def reload(self) -> Container:
        return await self._api.get(self.id)

    async def stop(self, timeout: int = 10) -> None:
        await self._api.stop(self.id, timeout=timeout)

    async def remove(self, force: bool = False) -> None:
        await self._api.remove(self.id, force=force)

    async def restart(self) -> None:
        await self._api.restart(self.id)

    async def pause(self) -> None:
        await self._api.pause(self.id)

    async def unpause(self) -> None:
        await self._api.unpause(self.id)

    async def rename(self, name: str) -> None:
        await self._api.rename(self.id, name)

    async def wait(self) -> int:
        return await self._api.wait(self.id)

    async def exec(self, cmd: list[str]) -> ExecResult:
        return await self._api.exec_run(self.id, cmd)

    async def stats(self) -> ContainerStats:
        return await self._api.stats(self.id)

    def logs(self, *, follow: bool = False, tail: int = 100) -> AsyncIterator[LogLine]:
        return self._api.logs(self.id, follow=follow, tail=tail)

    def stats_stream(self) -> AsyncIterator[ContainerStats]:
        return self._api.stats_stream(self.id)


def _parse_container(data: dict[str, Any], api: ContainersAPI) -> Container:
    """Parse Docker API JSON into a Container snapshot."""
    # Handle both /containers/json (list) and /containers/{id}/json (inspect) formats
    if "Name" in data:
        # inspect format
        name = data["Name"].lstrip("/")
        image = data.get("Config", {}).get("Image", "")
        labels = data.get("Config", {}).get("Labels") or {}
        status = data.get("State", {}).get("Status", "unknown")
        env_list = data.get("Config", {}).get("Env") or []
        ports = data.get("NetworkSettings", {}).get("Ports") or {}
    else:
        # list format
        names = data.get("Names", [])
        name = names[0].lstrip("/") if names else ""
        image = data.get("Image", "")
        labels = data.get("Labels") or {}
        status = data.get("State", data.get("Status", "unknown"))
        env_list = []
        ports_list = data.get("Ports") or []
        ports = {}
        for p in ports_list:
            key = f"{p.get('PrivatePort')}/{p.get('Type', 'tcp')}"
            ports.setdefault(key, []).append(p)

    env = {}
    for item in env_list:
        if "=" in item:
            k, v = item.split("=", 1)
            env[k] = v

    created_raw = data.get("Created", "")
    if isinstance(created_raw, int):
        created = datetime.fromtimestamp(created_raw)
    elif isinstance(created_raw, str) and created_raw:
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created = datetime.min
    else:
        created = datetime.min

    if isinstance(ports, dict) and "Name" in data:
        pass  # already parsed from inspect

    return Container(
        id=data.get("Id", ""),
        name=name,
        status=status,
        image=image,
        created=created,
        labels=labels,
        ports=ports,
        env=env,
        _api=api,
    )
