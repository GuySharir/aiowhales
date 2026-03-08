"""Additional container tests for coverage gaps."""

from __future__ import annotations

import json

import pytest

from aiowhales.api.containers import ContainersAPI
from aiowhales.models.container import ContainerStats
from aiowhales.testing import MockTransport

from .conftest import STATS_FIXTURE

# Minimal inspect fixture for create/run responses
_CREATED = {
    "Id": "new123",
    "Name": "/test",
    "Created": "2024-01-01T00:00:00Z",
    "State": {"Status": "created"},
    "Config": {"Image": "alpine", "Labels": {}, "Env": []},
    "NetworkSettings": {"Ports": {}},
}


@pytest.fixture
def api():
    transport = MockTransport()
    return ContainersAPI(transport), transport


class TestCreateWithEnv:
    @pytest.mark.asyncio
    async def test_create_with_env_dict(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register("GET", "/containers/new123/json", _CREATED)
        await containers_api.create("alpine", env={"FOO": "bar", "BAZ": "qux"})

    @pytest.mark.asyncio
    async def test_create_with_env_list(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register("GET", "/containers/new123/json", _CREATED)
        await containers_api.create("alpine", env=["FOO=bar"])

    @pytest.mark.asyncio
    async def test_create_with_labels(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register("GET", "/containers/new123/json", _CREATED)
        await containers_api.create("alpine", labels={"app": "test"})


class TestCreateWithPorts:
    @pytest.mark.asyncio
    async def test_create_with_ports(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register("GET", "/containers/new123/json", _CREATED)
        await containers_api.create("nginx", ports={"80": 8080, "443/tcp": 8443})

    @pytest.mark.asyncio
    async def test_create_with_ports_auto_tcp(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register("GET", "/containers/new123/json", _CREATED)
        # Port without /tcp suffix should get it added
        await containers_api.create("nginx", ports={80: 8080})


class TestRunWithOptions:
    @pytest.mark.asyncio
    async def test_run_with_env(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "r1"})
        transport.register("POST", "/containers/r1/start", {})
        transport.register("GET", "/containers/r1/json", {**_CREATED, "Id": "r1"})
        c = await containers_api.run("alpine", env={"X": "1"})
        assert c.id == "r1"

    @pytest.mark.asyncio
    async def test_run_with_ports(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "r1"})
        transport.register("POST", "/containers/r1/start", {})
        transport.register("GET", "/containers/r1/json", {**_CREATED, "Id": "r1"})
        c = await containers_api.run("nginx", ports={"80": 8080})
        assert c.id == "r1"

    @pytest.mark.asyncio
    async def test_run_with_labels(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "r1"})
        transport.register("POST", "/containers/r1/start", {})
        transport.register("GET", "/containers/r1/json", {**_CREATED, "Id": "r1"})
        c = await containers_api.run("alpine", labels={"app": "test"})
        assert c.id == "r1"


class TestRunContextContainerRemove:
    @pytest.mark.asyncio
    async def test_aexit_with_remove_on_exit(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "ctx1"})
        transport.register("POST", "/containers/ctx1/start", {})
        transport.register("GET", "/containers/ctx1/json", {**_CREATED, "Id": "ctx1"})
        transport.register("POST", "/containers/ctx1/stop", {})

        c = await containers_api.run("alpine", remove_on_exit=True)
        async with c:
            pass

        methods_and_paths = [(m, p) for m, p, _ in transport.calls]
        assert ("POST", "/containers/ctx1/stop") in methods_and_paths
        assert ("DELETE", "/containers/ctx1") in methods_and_paths

    @pytest.mark.asyncio
    async def test_aexit_without_remove(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "ctx2"})
        transport.register("POST", "/containers/ctx2/start", {})
        transport.register("GET", "/containers/ctx2/json", {**_CREATED, "Id": "ctx2"})
        transport.register("POST", "/containers/ctx2/stop", {})

        c = await containers_api.run("alpine", remove_on_exit=False)
        async with c:
            pass

        methods_and_paths = [(m, p) for m, p, _ in transport.calls]
        assert ("POST", "/containers/ctx2/stop") in methods_and_paths
        assert ("DELETE", "/containers/ctx2") not in methods_and_paths


class TestStatsStream:
    @pytest.mark.asyncio
    async def test_stats_stream_yields_stats(self, api):
        containers_api, transport = api
        chunk = json.dumps(STATS_FIXTURE).encode() + b"\n"
        transport.register_stream("GET", "/containers/abc/stats", [chunk])
        results = [s async for s in containers_api.stats_stream("abc")]
        assert len(results) == 1
        assert isinstance(results[0], ContainerStats)
        assert results[0].cpu_percent == 80.0


class TestLogs:
    @pytest.mark.asyncio
    async def test_logs_yields_lines(self, api):
        containers_api, transport = api
        # Docker log frame: 8-byte header + payload
        # stdout = stream type 1
        header = b"\x01\x00\x00\x00\x00\x00\x00\x05"
        payload = b"hello"
        transport.register_stream("GET", "/containers/abc/logs", [header + payload])
        lines = [line async for line in containers_api.logs("abc")]
        assert len(lines) >= 1
