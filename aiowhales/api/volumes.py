"""VolumesAPI — typed wrappers around Docker volume endpoints."""

from __future__ import annotations

from typing import Any

from ..models.volume import Volume, _parse_volume


class VolumesAPI:
    """API namespace for Docker volume operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(self) -> list[Volume]:
        data = await self._transport.get("/volumes")
        volumes = data.get("Volumes") or []
        return [_parse_volume(v) for v in volumes]

    async def get(self, name: str) -> Volume:
        data = await self._transport.get(f"/volumes/{name}")
        return _parse_volume(data)

    async def create(
        self,
        name: str,
        *,
        driver: str = "local",
        labels: dict[str, str] | None = None,
    ) -> Volume:
        body: dict[str, Any] = {"Name": name, "Driver": driver}
        if labels:
            body["Labels"] = labels
        data = await self._transport.post("/volumes/create", body)
        return _parse_volume(data)

    async def remove(self, name: str, force: bool = False) -> None:
        params: dict[str, Any] = {}
        if force:
            params["force"] = "true"
        await self._transport.delete(f"/volumes/{name}", **params)

    async def prune(self) -> list[str]:
        data = await self._transport.post("/volumes/prune")
        return data.get("VolumesDeleted") or []
