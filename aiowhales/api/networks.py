"""NetworksAPI — typed wrappers around Docker network endpoints."""

from __future__ import annotations

from typing import Any

from ..models.network import Network, _parse_network


class NetworksAPI:
    """API namespace for Docker network operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(self) -> list[Network]:
        data = await self._transport.get("/networks")
        return [_parse_network(n) for n in data]

    async def get(self, id: str) -> Network:
        data = await self._transport.get(f"/networks/{id}")
        return _parse_network(data)

    async def create(
        self,
        name: str,
        *,
        driver: str = "bridge",
        labels: dict[str, str] | None = None,
    ) -> Network:
        body: dict[str, Any] = {"Name": name, "Driver": driver}
        if labels:
            body["Labels"] = labels
        data = await self._transport.post("/networks/create", body)
        network_id = data.get("Id", "")
        return await self.get(network_id)

    async def remove(self, id: str) -> None:
        await self._transport.delete(f"/networks/{id}")

    async def connect(self, network_id: str, container_id: str, **aliases: Any) -> None:
        body: dict[str, Any] = {"Container": container_id}
        if aliases:
            body["EndpointConfig"] = {"Aliases": list(aliases.values())}
        await self._transport.post(f"/networks/{network_id}/connect", body)

    async def disconnect(self, network_id: str, container_id: str) -> None:
        body = {"Container": container_id}
        await self._transport.post(f"/networks/{network_id}/disconnect", body)

    async def prune(self) -> list[str]:  # type: ignore[valid-type]
        data = await self._transport.post("/networks/prune")
        deleted = data.get("NetworksDeleted")
        if not isinstance(deleted, list):
            return []
        return [n.get("Name", n.get("Id", "")) for n in deleted]
