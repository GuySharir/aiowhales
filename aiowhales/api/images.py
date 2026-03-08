"""ImagesAPI — typed wrappers around Docker image endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ..models.image import (
    BuildOutput,
    Image,
    PullProgress,
    PushProgress,
    _parse_image,
)
from ..stream import json_stream


class ImagesAPI:
    """API namespace for Docker image operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(self, *, all: bool = False) -> list[Image]:
        params: dict[str, Any] = {}
        if all:
            params["all"] = "true"
        data = await self._transport.get("/images/json", **params)
        return [_parse_image(img) for img in data]

    async def get(self, name: str) -> Image:
        data = await self._transport.get(f"/images/{name}/json")
        return _parse_image(data)

    async def inspect(self, name: str) -> Image:
        return await self.get(name)

    async def remove(self, name: str, force: bool = False) -> None:
        params: dict[str, Any] = {}
        if force:
            params["force"] = "true"
        await self._transport.delete(f"/images/{name}", **params)

    async def tag(self, name: str, new_tag: str) -> None:
        repo, _, tag = new_tag.partition(":")
        params: dict[str, Any] = {"repo": repo}
        if tag:
            params["tag"] = tag
        await self._transport.post(f"/images/{name}/tag", **params)

    async def pull(self, name: str) -> AsyncIterator[PullProgress]:
        repo, _, tag = name.partition(":")
        if not tag:
            tag = "latest"
        raw = self._transport.stream("POST", "/images/create", fromImage=repo, tag=tag)
        async for item in json_stream(raw):
            yield PullProgress(
                status=item.get("status", ""),
                layer_id=item.get("id", ""),
                progress=item.get("progress", ""),
                raw=item,
            )

    async def push(self, name: str) -> AsyncIterator[PushProgress]:
        raw = self._transport.stream("POST", f"/images/{name}/push")
        async for item in json_stream(raw):
            yield PushProgress(
                status=item.get("status", ""),
                layer_id=item.get("id", ""),
                progress=item.get("progress", ""),
                raw=item,
            )

    async def build(
        self,
        context: str,
        *,
        dockerfile: str = "Dockerfile",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[BuildOutput]:
        import io
        import tarfile

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(context, arcname=".")
        buf.seek(0)

        params: dict[str, Any] = {"dockerfile": dockerfile}
        if tags:
            params["t"] = tags[0]

        raw = self._transport.stream("POST", "/build", **params)
        async for item in json_stream(raw):
            yield BuildOutput(
                stream=item.get("stream", ""),
                error=item.get("error", ""),
                raw=item,
            )
