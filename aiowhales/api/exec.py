"""ExecAPI — exec operations on containers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ..models.exec_result import ExecResult
from ..stream import decode_stream


class ExecAPI:
    """API namespace for Docker exec operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(
        self,
        container_id: str,
        cmd: list[str],
        *,
        attach_stdout: bool = True,
        attach_stderr: bool = True,
        tty: bool = False,
        env: list[str] | None = None,
        workdir: str | None = None,
    ) -> str:
        """Create an exec instance and return its ID."""
        body: dict[str, Any] = {
            "AttachStdout": attach_stdout,
            "AttachStderr": attach_stderr,
            "Tty": tty,
            "Cmd": cmd,
        }
        if env:
            body["Env"] = env
        if workdir:
            body["WorkingDir"] = workdir
        data = await self._transport.post(f"/containers/{container_id}/exec", body)
        return data.get("Id", "")

    async def start(self, exec_id: str, *, detach: bool = False, tty: bool = False) -> str:
        """Start an exec instance and return its output."""
        body = {"Detach": detach, "Tty": tty}
        result = await self._transport.post(f"/exec/{exec_id}/start", body)
        return result if isinstance(result, str) else ""

    async def inspect(self, exec_id: str) -> dict[str, Any]:
        """Inspect an exec instance."""
        return await self._transport.get(f"/exec/{exec_id}/json")

    async def run(self, container_id: str, cmd: list[str], **kwargs: Any) -> ExecResult:
        """Create, start, and inspect an exec — convenience method."""
        exec_id = await self.create(container_id, cmd, **kwargs)
        output = await self.start(exec_id)
        info = await self.inspect(exec_id)
        return ExecResult(exit_code=info.get("ExitCode", -1), output=output)

    async def stream(self, container_id: str, cmd: list[str], **kwargs: Any) -> AsyncIterator[str]:
        """Create and start an exec, streaming output line by line."""
        exec_id = await self.create(container_id, cmd, **kwargs)
        body = {"Detach": False, "Tty": False}
        raw = self._transport.stream("POST", f"/exec/{exec_id}/start")
        async for line in decode_stream(raw):
            yield line
