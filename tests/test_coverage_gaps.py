"""Tests covering remaining coverage gaps across models, exec, images, compose."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from aiowhales.api.compose import ComposeAPI
from aiowhales.api.exec import ExecAPI
from aiowhales.api.images import ImagesAPI
from aiowhales.models.container import _parse_container
from aiowhales.models.image import Image, _parse_image
from aiowhales.models.network import _parse_network
from aiowhales.testing import MockTransport

# -- Model coverage gaps ------------------------------------------------------


class TestParseContainerEdgeCases:
    """Cover lines 62, 65, 74, 77 in models/container.py."""

    def test_inspect_format_with_created_int(self):
        """Created as integer timestamp in inspect format."""
        api = object()  # dummy
        data = {
            "Id": "abc",
            "Name": "/test",
            "Created": 1700000000,
            "State": {"Status": "running"},
            "Config": {"Image": "nginx", "Labels": None, "Env": None},
            "NetworkSettings": {"Ports": None},
        }
        c = _parse_container(data, api)
        assert c.name == "test"
        assert isinstance(c.created, datetime)

    def test_inspect_format_invalid_created_string(self):
        api = object()
        data = {
            "Id": "abc",
            "Name": "/test",
            "Created": "not-a-date",
            "State": {"Status": "running"},
            "Config": {"Image": "nginx", "Labels": {}, "Env": []},
            "NetworkSettings": {"Ports": {}},
        }
        c = _parse_container(data, api)
        assert c.created == datetime.min

    def test_inspect_format_empty_created(self):
        api = object()
        data = {
            "Id": "abc",
            "Name": "/test",
            "Created": "",
            "State": {"Status": "running"},
            "Config": {"Image": "nginx", "Labels": {}, "Env": []},
            "NetworkSettings": {"Ports": {}},
        }
        c = _parse_container(data, api)
        assert c.created == datetime.min

    def test_list_format_empty_names(self):
        api = object()
        data = {
            "Id": "abc",
            "Names": [],
            "Image": "nginx",
            "State": "running",
            "Created": 0,
            "Labels": {},
            "Ports": [],
        }
        c = _parse_container(data, api)
        assert c.name == ""

    def test_list_format_with_status_fallback(self):
        """Line 97: State fallback to Status."""
        api = object()
        data = {
            "Id": "abc",
            "Names": ["/test"],
            "Image": "nginx",
            "Status": "Up 2 hours",
            "Created": 0,
            "Labels": {},
            "Ports": [],
        }
        c = _parse_container(data, api)
        assert c.status == "Up 2 hours"


class TestParseImageEdgeCases:
    """Cover lines 64-65 and 66-67 in models/image.py."""

    def test_invalid_created_string(self):
        data = {
            "Id": "sha256:abc",
            "RepoTags": [],
            "Size": 100,
            "Created": "bad-date",
        }
        img = _parse_image(data)
        assert img.created == datetime.min

    def test_empty_created_string(self):
        data = {
            "Id": "sha256:abc",
            "RepoTags": [],
            "Size": 100,
            "Created": "",
        }
        img = _parse_image(data)
        assert img.created == datetime.min

    def test_non_string_non_int_created(self):
        data = {
            "Id": "sha256:abc",
            "RepoTags": [],
            "Size": 100,
            "Created": None,
        }
        img = _parse_image(data)
        assert img.created == datetime.min

    def test_short_id_non_sha256(self):
        img = Image(
            id="abcdef123456789",
            tags=[],
            size=0,
            created=datetime.min,
            labels={},
            architecture="",
            os="",
        )
        assert img.short_id == "abcdef123456"


class TestParseNetworkEdgeCases:
    """Cover lines 28-29 in models/network.py."""

    def test_invalid_created(self):
        data = {
            "Id": "net1",
            "Name": "bridge",
            "Driver": "bridge",
            "Scope": "local",
            "Labels": {},
            "Created": "bad-date",
        }
        n = _parse_network(data)
        assert n.created == datetime.min

    def test_empty_created(self):
        data = {
            "Id": "net1",
            "Name": "bridge",
            "Driver": "bridge",
            "Scope": "local",
            "Labels": {},
            "Created": "",
        }
        n = _parse_network(data)
        assert n.created == datetime.min


# -- ExecAPI coverage gaps ----------------------------------------------------


class TestExecAPICreateOptions:
    """Cover lines 38, 40 in exec.py (env and workdir params)."""

    @pytest.mark.asyncio
    async def test_create_with_env(self):
        transport = MockTransport()
        api = ExecAPI(transport)
        transport.register("POST", "/containers/abc/exec", {"Id": "exec1"})
        exec_id = await api.create("abc", ["ls"], env=["FOO=bar"])
        assert exec_id == "exec1"

    @pytest.mark.asyncio
    async def test_create_with_workdir(self):
        transport = MockTransport()
        api = ExecAPI(transport)
        transport.register("POST", "/containers/abc/exec", {"Id": "exec1"})
        exec_id = await api.create("abc", ["ls"], workdir="/app")
        assert exec_id == "exec1"

    @pytest.mark.asyncio
    async def test_create_with_env_and_workdir(self):
        transport = MockTransport()
        api = ExecAPI(transport)
        transport.register("POST", "/containers/abc/exec", {"Id": "exec1"})
        exec_id = await api.create("abc", ["ls"], env=["FOO=bar"], workdir="/app")
        assert exec_id == "exec1"


# -- ImagesAPI coverage gaps --------------------------------------------------


class TestImagesPush:
    """Cover lines 65-67 in images.py (push method)."""

    @pytest.mark.asyncio
    async def test_push_streams_progress(self):
        transport = MockTransport()
        api = ImagesAPI(transport)
        chunk = json.dumps({"status": "Pushing", "id": "layer1", "progress": "50%"}).encode()
        transport.register_stream("POST", "/images/myimg/push", [chunk + b"\n"])
        results = [p async for p in api.push("myimg")]
        assert len(results) == 1
        assert results[0].status == "Pushing"
        assert results[0].layer_id == "layer1"


# -- ComposeAPI coverage gaps -------------------------------------------------


class FakeProcess:
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
    def __init__(self, lines, returncode=0):
        self.returncode = returncode
        self.stdout = FakeStreamReader(lines)

    async def wait(self):
        return self.returncode

    def kill(self):
        pass


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


class TestComposeUpStreamWithOptions:
    """Cover lines 69, 72 in compose.py."""

    @pytest.mark.asyncio
    async def test_up_stream_with_build(self):
        compose = ComposeAPI()
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess([], returncode=0)
            _ = [line async for line in compose.up_stream("/app", build=True)]
            args = mock_exec.call_args[0]
            assert "--build" in args

    @pytest.mark.asyncio
    async def test_up_stream_with_services(self):
        compose = ComposeAPI()
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess([], returncode=0)
            _ = [line async for line in compose.up_stream("/app", services=["web", "db"])]
            args = mock_exec.call_args[0]
            assert "web" in args
            assert "db" in args


class TestComposeLogsEdgeCases:
    """Cover lines 157-158, 170 in compose.py."""

    @pytest.mark.asyncio
    async def test_logs_follow_with_service(self):
        compose = ComposeAPI()
        lines = [b"log1\n", b"log2\n"]
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeStreamProcess(lines, returncode=0)
            result = [line async for line in compose.logs("/app", service="web", follow=True)]
            assert len(result) == 2
            args = mock_exec.call_args[0]
            assert "--follow" in args
            assert "web" in args


class TestComposeBuildWithServices:
    """Cover line 170 in compose.py."""

    @pytest.mark.asyncio
    async def test_build_with_services(self):
        compose = ComposeAPI()
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0)
            await compose.build("/app", services=["web", "api"])
            args = mock_exec.call_args[0]
            assert "build" in args
            assert "web" in args
            assert "api" in args


class TestComposePsNameFallback:
    """Cover Name fallback in ps() line 116."""

    @pytest.mark.asyncio
    async def test_ps_uses_name_when_no_service_key(self):
        compose = ComposeAPI()
        output = json.dumps({"Name": "web-1", "State": "running", "ID": "abc", "Image": "nginx"})
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = FakeProcess(0, stdout=output.encode())
            result = await compose.ps("/app")
            assert result[0].name == "web-1"
