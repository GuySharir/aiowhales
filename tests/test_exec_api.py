"""Tests for ExecAPI."""

import pytest

from aiowhales.api.exec import ExecAPI
from aiowhales.models.exec_result import ExecResult
from aiowhales.testing import MockTransport


@pytest.fixture
def api():
    transport = MockTransport()
    return ExecAPI(transport), transport


class TestExecCreate:
    @pytest.mark.asyncio
    async def test_create_returns_id(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        exec_id = await exec_api.create("abc", ["ls", "-la"])
        assert exec_id == "exec123"

    @pytest.mark.asyncio
    async def test_create_correct_endpoint(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        await exec_api.create("abc", ["ls"])
        assert transport.calls[0][1] == "/containers/abc/exec"


class TestExecStart:
    @pytest.mark.asyncio
    async def test_start_returns_output(self, api):
        exec_api, transport = api
        transport.register("POST", "/exec/exec123/start", "hello world")
        output = await exec_api.start("exec123")
        assert output == "hello world"

    @pytest.mark.asyncio
    async def test_start_non_string_returns_empty(self, api):
        exec_api, transport = api
        transport.register("POST", "/exec/exec123/start", {"not": "a string"})
        output = await exec_api.start("exec123")
        assert output == ""


class TestExecInspect:
    @pytest.mark.asyncio
    async def test_inspect_returns_dict(self, api):
        exec_api, transport = api
        transport.register("GET", "/exec/exec123/json", {"ExitCode": 0, "Running": False})
        result = await exec_api.inspect("exec123")
        assert result["ExitCode"] == 0
        assert result["Running"] is False


class TestExecRun:
    @pytest.mark.asyncio
    async def test_run_success(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        transport.register("POST", "/exec/exec123/start", "output text")
        transport.register("GET", "/exec/exec123/json", {"ExitCode": 0})
        result = await exec_api.run("abc", ["echo", "hello"])
        assert isinstance(result, ExecResult)
        assert result.exit_code == 0
        assert result.output == "output text"

    @pytest.mark.asyncio
    async def test_run_failure(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec456"})
        transport.register("POST", "/exec/exec456/start", "error message")
        transport.register("GET", "/exec/exec456/json", {"ExitCode": 127})
        result = await exec_api.run("abc", ["nonexistent-command"])
        assert result.exit_code == 127

    @pytest.mark.asyncio
    async def test_run_calls_create_start_inspect(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec789"})
        transport.register("POST", "/exec/exec789/start", "")
        transport.register("GET", "/exec/exec789/json", {"ExitCode": 0})
        await exec_api.run("abc", ["ls"])
        paths = [call[1] for call in transport.calls]
        assert "/containers/abc/exec" in paths
        assert "/exec/exec789/start" in paths
        assert "/exec/exec789/json" in paths


class TestExecStream:
    @pytest.mark.asyncio
    async def test_stream_yields_lines(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec123"})
        transport.register_stream(
            "POST",
            "/exec/exec123/start",
            [
                b"line one\n",
                b"line two\n",
            ],
        )
        lines = [line async for line in exec_api.stream("abc", ["tail", "-f", "/log"])]
        assert lines == ["line one", "line two"]

    @pytest.mark.asyncio
    async def test_stream_empty(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec456"})
        transport.register_stream("POST", "/exec/exec456/start", [])
        lines = [line async for line in exec_api.stream("abc", ["echo"])]
        assert lines == []

    @pytest.mark.asyncio
    async def test_stream_calls_create_then_start(self, api):
        exec_api, transport = api
        transport.register("POST", "/containers/abc/exec", {"Id": "exec789"})
        transport.register_stream("POST", "/exec/exec789/start", [])
        _ = [line async for line in exec_api.stream("abc", ["ls"])]
        paths = [call[1] for call in transport.calls]
        assert paths[0] == "/containers/abc/exec"
        assert paths[1] == "/exec/exec789/start"
