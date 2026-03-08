"""ContainersAPI — typed wrappers around Docker container endpoints."""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

from ..models.container import Container, ContainerStats, _parse_container
from ..models.exec_result import ExecResult
from ..stream import LogLine, demux_log_stream


class ContainersAPI:
    """API namespace for Docker container operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(
        self, *, all: bool = False, filters: dict[str, Any] | None = None
    ) -> list[Container]:
        params: dict[str, Any] = {}
        if all:
            params["all"] = "true"
        if filters:
            params["filters"] = json.dumps(filters)
        data = await self._transport.get("/containers/json", **params)
        return [_parse_container(c, self) for c in data]

    async def get(self, id: str) -> Container:
        data = await self._transport.get(f"/containers/{id}/json")
        return _parse_container(data, self)

    async def create(self, image: str, **kwargs: Any) -> Container:
        body: dict[str, Any] = {"Image": image}
        if "command" in kwargs:
            cmd = kwargs.pop("command")
            body["Cmd"] = cmd if isinstance(cmd, list) else [cmd]
        name = kwargs.pop("name") if "name" in kwargs else None
        if "env" in kwargs:
            env = kwargs.pop("env")
            body["Env"] = [f"{k}={v}" for k, v in env.items()] if isinstance(env, dict) else env
        if "labels" in kwargs:
            body["Labels"] = kwargs.pop("labels")

        host_config: dict[str, Any] = {}
        if "ports" in kwargs:
            ports = kwargs.pop("ports")
            exposed: dict[str, dict[str, Any]] = {}
            port_bindings: dict[str, list[dict[str, str]]] = {}
            for container_port, host_port in ports.items():
                port_str = str(container_port)
                key = f"{container_port}/tcp" if "/" not in port_str else port_str
                exposed[key] = {}
                port_bindings[key] = [{"HostPort": str(host_port)}]
            body["ExposedPorts"] = exposed
            host_config["PortBindings"] = port_bindings

        if host_config:
            body["HostConfig"] = host_config

        params: dict[str, Any] = {}
        if name:
            params["name"] = name

        data = await self._transport.post("/containers/create", body, **params)
        container_id = data.get("Id", "")
        return await self.get(container_id)

    async def run(
        self,
        image: str,
        command: list[str] | str | None = None,
        *,
        name: str | None = None,
        env: dict[str, str] | None = None,
        ports: dict[str, int] | None = None,
        detach: bool = True,
        remove_on_exit: bool = False,
        labels: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Container:
        create_kwargs: dict[str, Any] = {}
        if command is not None:
            create_kwargs["command"] = command
        if name:
            create_kwargs["name"] = name
        if env:
            create_kwargs["env"] = env
        if ports:
            create_kwargs["ports"] = ports
        if labels:
            create_kwargs["labels"] = labels
        create_kwargs.update(kwargs)

        container = await self.create(image, **create_kwargs)
        await self.start(container.id)

        if not detach:
            await self.wait(container.id)
            container = await self.get(container.id)

        return _RunContextContainer(container, self, remove_on_exit)

    async def start(self, id: str) -> None:
        await self._transport.post(f"/containers/{id}/start")

    async def stop(self, id: str, timeout: int = 10) -> None:
        await self._transport.post(f"/containers/{id}/stop", t=timeout)

    async def remove(self, id: str, force: bool = False) -> None:
        params: dict[str, Any] = {}
        if force:
            params["force"] = "true"
        await self._transport.delete(f"/containers/{id}", **params)

    async def restart(self, id: str) -> None:
        await self._transport.post(f"/containers/{id}/restart")

    async def rename(self, id: str, name: str) -> None:
        await self._transport.post(f"/containers/{id}/rename", name=name)

    async def pause(self, id: str) -> None:
        await self._transport.post(f"/containers/{id}/pause")

    async def unpause(self, id: str) -> None:
        await self._transport.post(f"/containers/{id}/unpause")

    async def wait(self, id: str) -> int:
        data = await self._transport.post(f"/containers/{id}/wait")
        return int(data.get("StatusCode", -1))

    async def stats(self, id: str) -> ContainerStats:
        data = await self._transport.get(f"/containers/{id}/stats", stream="false")
        return _parse_stats(data)

    async def logs(
        self, id: str, *, follow: bool = False, tail: int = 100
    ) -> AsyncIterator[LogLine]:
        params: dict[str, Any] = {
            "stdout": "true",
            "stderr": "true",
            "follow": str(follow).lower(),
            "tail": str(tail),
        }
        raw_stream = self._transport.stream("GET", f"/containers/{id}/logs", **params)
        async for line in demux_log_stream(raw_stream):
            yield line

    async def stats_stream(self, id: str) -> AsyncIterator[ContainerStats]:
        params: dict[str, Any] = {"stream": "true"}
        raw_stream = self._transport.stream("GET", f"/containers/{id}/stats", **params)
        from ..stream import json_stream

        async for data in json_stream(raw_stream):
            yield _parse_stats(data)

    async def exec_run(self, container_id: str, cmd: list[str]) -> ExecResult:
        """Create and start an exec instance, returning the result."""
        exec_body = {
            "AttachStdout": True,
            "AttachStderr": True,
            "Cmd": cmd,
        }
        exec_data = await self._transport.post(f"/containers/{container_id}/exec", exec_body)
        exec_id = exec_data.get("Id", "")

        start_body = {"Detach": False, "Tty": False}
        output = await self._transport.post(f"/exec/{exec_id}/start", start_body)
        output_str = output if isinstance(output, str) else ""

        inspect_data = await self._transport.get(f"/exec/{exec_id}/json")
        exit_code = inspect_data.get("ExitCode", -1)

        return ExecResult(exit_code=exit_code, output=output_str)


class _RunContextContainer(Container):
    """Container wrapper that supports async context manager for auto-removal."""

    def __init__(self, container: Container, api: ContainersAPI, remove_on_exit: bool) -> None:
        # Copy all fields from the wrapped container
        object.__setattr__(self, "_container", container)
        object.__setattr__(self, "_containers_api", api)
        object.__setattr__(self, "_remove_on_exit", remove_on_exit)
        # Forward frozen dataclass fields
        for f in Container.__dataclass_fields__:
            object.__setattr__(self, f, getattr(container, f))

    async def __aenter__(self) -> Container:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        api: ContainersAPI = object.__getattribute__(self, "_containers_api")
        remove: bool = object.__getattribute__(self, "_remove_on_exit")
        with contextlib.suppress(Exception):
            await api.stop(self.id, timeout=5)
        if remove:
            with contextlib.suppress(Exception):
                await api.remove(self.id, force=True)


def _parse_stats(data: dict[str, Any]) -> ContainerStats:
    """Parse Docker stats JSON into a ContainerStats snapshot."""
    cpu_stats = data.get("cpu_stats", {})
    precpu = data.get("precpu_stats", {})
    memory = data.get("memory_stats", {})

    cur_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    pre_usage = precpu.get("cpu_usage", {}).get("total_usage", 0)
    cpu_delta = cur_usage - pre_usage
    system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
    n_cpus = cpu_stats.get("online_cpus", 1)
    cpu_percent = (cpu_delta / system_delta * n_cpus * 100.0) if system_delta > 0 else 0.0

    mem_usage = memory.get("usage", 0)
    mem_limit = memory.get("limit", 1)

    networks = data.get("networks", {})
    rx = sum(v.get("rx_bytes", 0) for v in networks.values())
    tx = sum(v.get("tx_bytes", 0) for v in networks.values())

    return ContainerStats(
        cpu_percent=round(cpu_percent, 2),
        memory_mb=round(mem_usage / 1024 / 1024, 2),
        memory_limit_mb=round(mem_limit / 1024 / 1024, 2),
        network_rx_bytes=rx,
        network_tx_bytes=tx,
        pids=data.get("pids_stats", {}).get("current", 0),
        raw=data,
    )
