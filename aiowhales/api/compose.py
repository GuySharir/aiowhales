"""ComposeAPI — Docker Compose operations via asyncio subprocess."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ..exceptions import ComposeError


@dataclass(frozen=True)
class ComposeService:
    """Snapshot of a Compose service status."""

    name: str
    state: str
    id: str
    image: str


class ComposeAPI:
    """API namespace for Docker Compose operations.

    All operations delegate to the ``docker compose`` CLI via
    ``asyncio.create_subprocess_exec``. From the caller's perspective,
    everything is fully async.
    """

    def __init__(self, compose_cmd: str = "docker") -> None:
        self._compose_cmd = compose_cmd

    def _base_args(self, project_dir: str) -> list[str]:
        return [self._compose_cmd, "compose", "--project-directory", project_dir]

    async def _run(self, project_dir: str, *args: str) -> str:
        cmd = self._base_args(project_dir) + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ComposeError(proc.returncode or 1, stderr.decode("utf-8", errors="replace"))
        return stdout.decode("utf-8", errors="replace")

    async def up(
        self,
        project_dir: str,
        *,
        detach: bool = True,
        build: bool = False,
        services: list[str] | None = None,
    ) -> None:
        args = ["up"]
        if detach:
            args.append("-d")
        if build:
            args.append("--build")
        if services:
            args.extend(services)
        await self._run(project_dir, *args)

    async def up_stream(self, project_dir: str, **kwargs: Any) -> AsyncIterator[str]:
        args = ["up"]
        if kwargs.get("build"):
            args.append("--build")
        services = kwargs.get("services")
        if services:
            args.extend(services)
        cmd = self._base_args(project_dir) + args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        try:
            async for line in proc.stdout:
                yield line.decode("utf-8", errors="replace").rstrip("\n")
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
        returncode = await proc.wait()
        if returncode != 0:
            raise ComposeError(returncode, "docker compose up failed")

    async def down(
        self,
        project_dir: str,
        *,
        volumes: bool = False,
        remove_orphans: bool = False,
    ) -> None:
        args = ["down"]
        if volumes:
            args.append("--volumes")
        if remove_orphans:
            args.append("--remove-orphans")
        await self._run(project_dir, *args)

    async def ps(self, project_dir: str) -> list[ComposeService]:
        output = await self._run(project_dir, "ps", "--format", "json")
        import json

        services = []
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            services.append(
                ComposeService(
                    name=data.get("Service", data.get("Name", "")),
                    state=data.get("State", ""),
                    id=data.get("ID", ""),
                    image=data.get("Image", ""),
                )
            )
        return services

    async def run(self, project_dir: str, service: str, command: str | list[str]) -> str:
        args = ["run", "--rm", service]
        if isinstance(command, list):
            args.extend(command)
        else:
            args.append(command)
        return await self._run(project_dir, *args)

    async def logs(
        self,
        project_dir: str,
        *,
        service: str | None = None,
        follow: bool = False,
    ) -> AsyncIterator[str]:
        args = ["logs"]
        if follow:
            args.append("--follow")
        if service:
            args.append(service)
        if follow:
            cmd = self._base_args(project_dir) + args
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            try:
                async for line in proc.stdout:
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
                else:
                    await proc.wait()
        else:
            output = await self._run(project_dir, *args)
            for text_line in output.splitlines():
                yield text_line

    async def build(self, project_dir: str, **kwargs: Any) -> None:
        args = ["build"]
        services = kwargs.get("services")
        if services:
            args.extend(services)
        await self._run(project_dir, *args)

    async def pull(self, project_dir: str) -> None:
        await self._run(project_dir, "pull")

    async def restart(self, project_dir: str, service: str | None = None) -> None:
        args = ["restart"]
        if service:
            args.append(service)
        await self._run(project_dir, *args)
