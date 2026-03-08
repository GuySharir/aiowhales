"""Tests for ComposeAPI."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from aiowhales.api.compose import ComposeAPI, ComposeService
from aiowhales.exceptions import ComposeError


class FakeProcess:
    """Fake asyncio.subprocess.Process for testing."""

    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.stdout = None

    async def communicate(self):
        return self._stdout, self._stderr

    async def wait(self):
        return self.returncode


class FakeStreamProcess:
    """Fake Process with a streaming stdout."""

    def __init__(self, lines, returncode=0):
        self.returncode = returncode
        self.stdout = FakeStreamReader(lines)

    async def wait(self):
        return self.returncode


class FakeStreamReader:
    def __init__(self, lines):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration from None


@pytest.fixture
def compose():
    return ComposeAPI()


class TestComposeUp:
    @pytest.mark.asyncio
    async def test_up_default_detached(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.up("/app")
            args = mock_exec.call_args[0]
            assert "up" in args
            assert "-d" in args

    @pytest.mark.asyncio
    async def test_up_with_build(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.up("/app", build=True)
            args = mock_exec.call_args[0]
            assert "--build" in args

    @pytest.mark.asyncio
    async def test_up_with_services(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.up("/app", services=["web", "db"])
            args = mock_exec.call_args[0]
            assert "web" in args
            assert "db" in args

    @pytest.mark.asyncio
    async def test_up_failure_raises_compose_error(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(1, stderr=b"service failed")
            with pytest.raises(ComposeError) as exc_info:
                await compose.up("/app")
            assert exc_info.value.returncode == 1
            assert "service failed" in exc_info.value.stderr

    @pytest.mark.asyncio
    async def test_up_not_detached(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.up("/app", detach=False)
            args = mock_exec.call_args[0]
            assert "-d" not in args


class TestComposeUpStream:
    @pytest.mark.asyncio
    async def test_up_stream_yields_lines(self, compose):
        lines = [b"Creating web...\n", b"Creating db...\n", b"Started\n"]
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess(lines, returncode=0)
            result = [line async for line in compose.up_stream("/app")]
            assert len(result) == 3
            assert result[0] == "Creating web..."

    @pytest.mark.asyncio
    async def test_up_stream_failure(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess([], returncode=1)
            with pytest.raises(ComposeError):
                _ = [line async for line in compose.up_stream("/app")]


class TestComposeDown:
    @pytest.mark.asyncio
    async def test_down_basic(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.down("/app")
            args = mock_exec.call_args[0]
            assert "down" in args

    @pytest.mark.asyncio
    async def test_down_with_volumes(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.down("/app", volumes=True)
            args = mock_exec.call_args[0]
            assert "--volumes" in args

    @pytest.mark.asyncio
    async def test_down_remove_orphans(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.down("/app", remove_orphans=True)
            args = mock_exec.call_args[0]
            assert "--remove-orphans" in args


class TestComposePs:
    @pytest.mark.asyncio
    async def test_ps_parses_services(self, compose):
        output = "\n".join(
            [
                json.dumps({"Service": "web", "State": "running", "ID": "abc", "Image": "nginx"}),
                json.dumps(
                    {"Service": "db", "State": "running", "ID": "def", "Image": "postgres"}
                ),
            ]
        )
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=output.encode())
            result = await compose.ps("/app")
            assert len(result) == 2
            assert all(isinstance(s, ComposeService) for s in result)
            assert result[0].name == "web"
            assert result[1].name == "db"

    @pytest.mark.asyncio
    async def test_ps_empty(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"")
            result = await compose.ps("/app")
            assert result == []

    @pytest.mark.asyncio
    async def test_ps_uses_json_format(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"")
            await compose.ps("/app")
            args = mock_exec.call_args[0]
            assert "--format" in args
            assert "json" in args


class TestComposeRun:
    @pytest.mark.asyncio
    async def test_run_with_string_command(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"output")
            result = await compose.run("/app", "web", "ls -la")
            assert result == "output"

    @pytest.mark.asyncio
    async def test_run_with_list_command(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"result")
            await compose.run("/app", "web", ["python", "-c", "print(1)"])
            args = mock_exec.call_args[0]
            assert "python" in args
            assert "-c" in args

    @pytest.mark.asyncio
    async def test_run_includes_rm_flag(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"")
            await compose.run("/app", "web", "ls")
            args = mock_exec.call_args[0]
            assert "--rm" in args


class TestComposeLogs:
    @pytest.mark.asyncio
    async def test_logs_non_follow(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"line1\nline2\nline3")
            lines = [line async for line in compose.logs("/app")]
            assert lines == ["line1", "line2", "line3"]

    @pytest.mark.asyncio
    async def test_logs_with_service(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=b"log")
            _ = [line async for line in compose.logs("/app", service="web")]
            args = mock_exec.call_args[0]
            assert "web" in args

    @pytest.mark.asyncio
    async def test_logs_follow(self, compose):
        lines = [b"streaming line 1\n", b"streaming line 2\n"]
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess(lines, returncode=0)
            result = [line async for line in compose.logs("/app", follow=True)]
            assert len(result) == 2


class TestComposeBuild:
    @pytest.mark.asyncio
    async def test_build(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.build("/app")
            args = mock_exec.call_args[0]
            assert "build" in args

    @pytest.mark.asyncio
    async def test_build_failure(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(1, stderr=b"build failed")
            with pytest.raises(ComposeError):
                await compose.build("/app")


class TestComposePull:
    @pytest.mark.asyncio
    async def test_pull(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.pull("/app")
            args = mock_exec.call_args[0]
            assert "pull" in args


class TestComposeRestart:
    @pytest.mark.asyncio
    async def test_restart_all(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.restart("/app")
            args = mock_exec.call_args[0]
            assert "restart" in args

    @pytest.mark.asyncio
    async def test_restart_specific_service(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.restart("/app", service="web")
            args = mock_exec.call_args[0]
            assert "web" in args


class TestComposeProjectDir:
    @pytest.mark.asyncio
    async def test_project_dir_passed(self, compose):
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.up("/my/project")
            args = mock_exec.call_args[0]
            assert "--project-directory" in args
            idx = list(args).index("--project-directory")
            assert args[idx + 1] == "/my/project"


class TestComposeService:
    def test_frozen(self):
        s = ComposeService(name="web", state="running", id="abc", image="nginx")
        with pytest.raises(AttributeError):
            s.name = "other"

    def test_attributes(self):
        s = ComposeService(name="web", state="running", id="abc", image="nginx:latest")
        assert s.name == "web"
        assert s.state == "running"
        assert s.id == "abc"
        assert s.image == "nginx:latest"
