"""Tests for ContainersAPI."""

import pytest

from aiowhales import AsyncDockerClient
from aiowhales.api.containers import ContainersAPI, _parse_stats
from aiowhales.models.container import Container, ContainerStats
from aiowhales.models.exec_result import ExecResult
from aiowhales.testing import MockTransport

from .conftest import (
    CONTAINER_INSPECT_FIXTURE,
    CONTAINER_LIST_FIXTURE,
    STATS_FIXTURE,
)


@pytest.fixture
def api():
    transport = MockTransport()
    return ContainersAPI(transport), transport


class TestContainersList:
    @pytest.mark.asyncio
    async def test_list_returns_containers(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        result = await containers_api.list()
        assert len(result) == 2
        assert all(isinstance(c, Container) for c in result)

    @pytest.mark.asyncio
    async def test_list_names(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        result = await containers_api.list()
        assert result[0].name == "web-app"
        assert result[1].name == "db"

    @pytest.mark.asyncio
    async def test_list_all_param(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", [])
        await containers_api.list(all=True)
        call = transport.calls[0]
        assert call[2].get("all") == "true"

    @pytest.mark.asyncio
    async def test_list_with_filters(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", [])
        await containers_api.list(filters={"status": ["running"]})
        call = transport.calls[0]
        assert "filters" in call[2]

    @pytest.mark.asyncio
    async def test_list_empty(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", [])
        result = await containers_api.list()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_default_no_all_param(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/json", [])
        await containers_api.list()
        call = transport.calls[0]
        assert "all" not in call[2]


class TestContainersGet:
    @pytest.mark.asyncio
    async def test_get_by_id(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc123def456/json", CONTAINER_INSPECT_FIXTURE)
        c = await containers_api.get("abc123def456")
        assert c.id == "abc123def456"
        assert c.name == "web-app"
        assert c.status == "running"

    @pytest.mark.asyncio
    async def test_get_parses_env(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/json", CONTAINER_INSPECT_FIXTURE)
        c = await containers_api.get("abc")
        assert c.env["FOO"] == "bar"
        assert c.env["DEBUG"] == "1"


class TestContainersCreate:
    @pytest.mark.asyncio
    async def test_create_basic(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register(
            "GET",
            "/containers/new123/json",
            {
                "Id": "new123",
                "Name": "/my-container",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "created"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        c = await containers_api.create("alpine")
        assert c.id == "new123"

    @pytest.mark.asyncio
    async def test_create_with_name(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register(
            "GET",
            "/containers/new123/json",
            {
                "Id": "new123",
                "Name": "/test",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "created"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        await containers_api.create("alpine", name="test")
        # Verify name param was passed
        create_call = transport.calls[0]
        assert create_call[2].get("name") == "test"

    @pytest.mark.asyncio
    async def test_create_with_command_list(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register(
            "GET",
            "/containers/new123/json",
            {
                "Id": "new123",
                "Name": "/t",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "created"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        await containers_api.create("alpine", command=["echo", "hello"])

    @pytest.mark.asyncio
    async def test_create_with_command_string(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "new123"})
        transport.register(
            "GET",
            "/containers/new123/json",
            {
                "Id": "new123",
                "Name": "/t",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "created"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        await containers_api.create("alpine", command="echo hello")


class TestContainersRun:
    @pytest.mark.asyncio
    async def test_run_detached(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "run123"})
        transport.register("POST", "/containers/run123/start", {})
        transport.register(
            "GET",
            "/containers/run123/json",
            {
                "Id": "run123",
                "Name": "/runner",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "running"},
                "Config": {"Image": "nginx", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        c = await containers_api.run("nginx", name="runner")
        assert c.id == "run123"

    @pytest.mark.asyncio
    async def test_run_not_detached_waits(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "run123"})
        transport.register("POST", "/containers/run123/start", {})
        transport.register("POST", "/containers/run123/wait", {"StatusCode": 0})
        transport.register(
            "GET",
            "/containers/run123/json",
            {
                "Id": "run123",
                "Name": "/runner",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "exited"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        c = await containers_api.run("alpine", command=["echo", "hi"], detach=False)
        assert c.id == "run123"

    @pytest.mark.asyncio
    async def test_run_context_manager(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/create", {"Id": "ctx123"})
        transport.register("POST", "/containers/ctx123/start", {})
        transport.register(
            "GET",
            "/containers/ctx123/json",
            {
                "Id": "ctx123",
                "Name": "/ctx",
                "Created": "2024-01-01T00:00:00Z",
                "State": {"Status": "running"},
                "Config": {"Image": "alpine", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}},
            },
        )
        transport.register("POST", "/containers/ctx123/stop", {})

        c = await containers_api.run("alpine", remove_on_exit=True)
        async with c as container:
            assert container.id == "ctx123"
        # Verify stop and remove were called
        methods_and_paths = [(m, p) for m, p, _ in transport.calls]
        assert ("POST", "/containers/ctx123/stop") in methods_and_paths


class TestContainerLifecycle:
    @pytest.mark.asyncio
    async def test_start(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/start", {})
        await containers_api.start("abc")
        assert transport.calls[0][1] == "/containers/abc/start"

    @pytest.mark.asyncio
    async def test_stop(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/stop", {})
        await containers_api.stop("abc", timeout=30)
        assert transport.calls[0][1] == "/containers/abc/stop"

    @pytest.mark.asyncio
    async def test_remove(self, api):
        containers_api, transport = api
        await containers_api.remove("abc")
        assert transport.calls[0] == ("DELETE", "/containers/abc", {})

    @pytest.mark.asyncio
    async def test_remove_force(self, api):
        containers_api, transport = api
        await containers_api.remove("abc", force=True)
        assert transport.calls[0][2].get("force") == "true"

    @pytest.mark.asyncio
    async def test_restart(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/restart", {})
        await containers_api.restart("abc")
        assert transport.calls[0][1] == "/containers/abc/restart"

    @pytest.mark.asyncio
    async def test_rename(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/rename", {})
        await containers_api.rename("abc", "new-name")
        assert transport.calls[0][2].get("name") == "new-name"

    @pytest.mark.asyncio
    async def test_pause(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/pause", {})
        await containers_api.pause("abc")
        assert transport.calls[0][1] == "/containers/abc/pause"

    @pytest.mark.asyncio
    async def test_unpause(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/unpause", {})
        await containers_api.unpause("abc")
        assert transport.calls[0][1] == "/containers/abc/unpause"

    @pytest.mark.asyncio
    async def test_wait(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/wait", {"StatusCode": 0})
        exit_code = await containers_api.wait("abc")
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_wait_nonzero_exit(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/wait", {"StatusCode": 137})
        exit_code = await containers_api.wait("abc")
        assert exit_code == 137


class TestContainerStats:
    @pytest.mark.asyncio
    async def test_stats_snapshot(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        assert isinstance(stats, ContainerStats)

    @pytest.mark.asyncio
    async def test_stats_cpu_percent(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        assert stats.cpu_percent == 80.0  # (100M/500M) * 4 * 100

    @pytest.mark.asyncio
    async def test_stats_memory(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        assert stats.memory_mb == 100.0

    @pytest.mark.asyncio
    async def test_stats_network(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        assert stats.network_rx_bytes == 1280000  # 1024000 + 256000
        assert stats.network_tx_bytes == 640000  # 512000 + 128000

    @pytest.mark.asyncio
    async def test_stats_pids(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        assert stats.pids == 5

    @pytest.mark.asyncio
    async def test_stats_frozen(self, api):
        containers_api, transport = api
        transport.register("GET", "/containers/abc/stats", STATS_FIXTURE)
        stats = await containers_api.stats("abc")
        with pytest.raises(AttributeError):
            stats.cpu_percent = 0.0


class TestParseStats:
    def test_zero_system_delta(self):
        """CPU percent should be 0 when there's no system delta."""
        data = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 100},
                "system_cpu_usage": 500,
                "online_cpus": 1,
            },
            "precpu_stats": {"cpu_usage": {"total_usage": 50}, "system_cpu_usage": 500},
            "memory_stats": {"usage": 0, "limit": 1},
        }
        stats = _parse_stats(data)
        assert stats.cpu_percent == 0.0

    def test_empty_stats(self):
        stats = _parse_stats({})
        assert stats.cpu_percent == 0.0
        assert stats.memory_mb == 0.0
        assert stats.pids == 0

    def test_no_networks(self):
        stats = _parse_stats({"networks": {}})
        assert stats.network_rx_bytes == 0
        assert stats.network_tx_bytes == 0

    def test_raw_preserved(self):
        data = {"custom_field": "test"}
        stats = _parse_stats(data)
        assert stats.raw == data


class TestContainerExecRun:
    @pytest.mark.asyncio
    async def test_exec_run(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        transport.register("POST", "/exec/exec123/start", "hello world")
        transport.register("GET", "/exec/exec123/json", {"ExitCode": 0})
        result = await containers_api.exec_run("abc", ["echo", "hello"])
        assert isinstance(result, ExecResult)
        assert result.exit_code == 0
        assert result.output == "hello world"

    @pytest.mark.asyncio
    async def test_exec_run_nonzero_exit(self, api):
        containers_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        transport.register("POST", "/exec/exec123/start", "error")
        transport.register("GET", "/exec/exec123/json", {"ExitCode": 1})
        result = await containers_api.exec_run("abc", ["false"])
        assert result.exit_code == 1


class TestContainerInstanceMethods:
    @pytest.mark.asyncio
    async def test_reload(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("GET", "/containers/abc123def456/json", CONTAINER_INSPECT_FIXTURE)
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            reloaded = await containers[0].reload()
            assert isinstance(reloaded, Container)
            assert reloaded.id == "abc123def456"

    @pytest.mark.asyncio
    async def test_stop_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("POST", "/containers/abc123def456/stop", {})
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            await containers[0].stop(timeout=5)

    @pytest.mark.asyncio
    async def test_remove_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            await containers[0].remove(force=True)

    @pytest.mark.asyncio
    async def test_restart_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("POST", "/containers/abc123def456/restart", {})
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            await containers[0].restart()

    @pytest.mark.asyncio
    async def test_pause_unpause_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("POST", "/containers/abc123def456/pause", {})
        transport.register("POST", "/containers/abc123def456/unpause", {})
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            await containers[0].pause()
            await containers[0].unpause()

    @pytest.mark.asyncio
    async def test_exec_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("POST", "/containers/abc123def456/exec", {"Id": "exec1"})
        transport.register("POST", "/exec/exec1/start", "output")
        transport.register("GET", "/exec/exec1/json", {"ExitCode": 0})
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            result = await containers[0].exec(["ls"])
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_stats_via_instance(self):
        transport = MockTransport()
        transport.register("GET", "/containers/json", CONTAINER_LIST_FIXTURE)
        transport.register("GET", "/containers/abc123def456/stats", STATS_FIXTURE)
        async with AsyncDockerClient(transport=transport) as docker:
            containers = await docker.containers.list()
            stats = await containers[0].stats()
            assert isinstance(stats, ContainerStats)
