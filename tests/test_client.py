"""Tests for AsyncDockerClient and from_env."""

import json
import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

from aiowhales import AsyncDockerClient, DockerClient, from_env
from aiowhales.api.compose import ComposeAPI
from aiowhales.api.containers import ContainersAPI
from aiowhales.api.exec import ExecAPI
from aiowhales.api.images import ImagesAPI
from aiowhales.api.networks import NetworksAPI
from aiowhales.api.volumes import VolumesAPI
from aiowhales.models.events import DockerEvent
from aiowhales.testing import MockTransport
from aiowhales.transport import TCPTransport, UnixSocketTransport

from .conftest import EVENT_FIXTURE


class TestClientInit:
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")
    async def test_default_transport_is_unix_socket(self):
        client = AsyncDockerClient()
        assert isinstance(client._transport, UnixSocketTransport)
        await client.aclose()

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    async def test_default_transport_is_tcp_on_windows(self):
        client = AsyncDockerClient()
        assert isinstance(client._transport, TCPTransport)
        await client.aclose()

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")
    async def test_unix_socket_path(self):
        client = AsyncDockerClient("/run/user/1000/docker.sock")
        assert isinstance(client._transport, UnixSocketTransport)
        assert client._transport.socket_path == "/run/user/1000/docker.sock"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_tcp_url(self):
        client = AsyncDockerClient("tcp://remote:2376")
        assert isinstance(client._transport, TCPTransport)
        await client.aclose()

    @pytest.mark.asyncio
    async def test_https_url(self):
        client = AsyncDockerClient("https://remote:2376")
        assert isinstance(client._transport, TCPTransport)
        await client.aclose()

    def test_custom_transport(self):
        transport = MockTransport()
        client = AsyncDockerClient(transport=transport)
        assert client._transport is transport

    def test_transport_takes_precedence_over_url(self):
        transport = MockTransport()
        client = AsyncDockerClient("tcp://remote:2376", transport=transport)
        assert client._transport is transport


class TestClientNamespaces:
    def test_has_containers(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.containers, ContainersAPI)

    def test_has_images(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.images, ImagesAPI)

    def test_has_volumes(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.volumes, VolumesAPI)

    def test_has_networks(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.networks, NetworksAPI)

    def test_has_exec(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.exec, ExecAPI)

    def test_has_compose(self):
        client = AsyncDockerClient(transport=MockTransport())
        assert isinstance(client.compose, ComposeAPI)


class TestClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self):
        transport = MockTransport()
        async with AsyncDockerClient(transport=transport) as client:
            assert isinstance(client, AsyncDockerClient)

    @pytest.mark.asyncio
    async def test_aclose(self):
        transport = MockTransport()
        client = AsyncDockerClient(transport=transport)
        await client.aclose()  # Should not raise


class TestClientAlias:
    def test_docker_client_is_async_docker_client(self):
        assert DockerClient is AsyncDockerClient


class TestFromEnv:
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")
    async def test_default_unix_socket(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DOCKER_HOST", None)
            client = from_env()
            assert isinstance(client._transport, UnixSocketTransport)
            await client.aclose()

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    async def test_default_tcp_on_windows(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DOCKER_HOST", None)
            client = from_env()
            assert isinstance(client._transport, TCPTransport)
            await client.aclose()

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")
    async def test_custom_docker_host_unix(self):
        with patch.dict(os.environ, {"DOCKER_HOST": "unix:///run/user/1000/docker.sock"}):
            client = from_env()
            assert isinstance(client._transport, UnixSocketTransport)
            assert client._transport.socket_path == "/run/user/1000/docker.sock"
            await client.aclose()

    @pytest.mark.asyncio
    async def test_custom_docker_host_tcp(self):
        with patch.dict(os.environ, {"DOCKER_HOST": "tcp://remote:2376"}):
            client = from_env()
            assert isinstance(client._transport, TCPTransport)
            await client.aclose()


class TestClientEvents:
    @pytest.mark.asyncio
    async def test_events_stream(self):
        transport = MockTransport()
        event_json = json.dumps(EVENT_FIXTURE).encode() + b"\n"
        transport.register_stream("GET", "/events", [event_json])
        async with AsyncDockerClient(transport=transport) as docker:
            events = [e async for e in docker.events()]
            assert len(events) == 1
            assert isinstance(events[0], DockerEvent)
            assert events[0].type == "container"
            assert events[0].action == "start"

    @pytest.mark.asyncio
    async def test_events_with_filters(self):
        transport = MockTransport()
        transport.register_stream("GET", "/events", [])
        async with AsyncDockerClient(transport=transport) as docker:
            _ = [e async for e in docker.events(filters={"type": ["container"]})]
            call = transport.calls[0]
            assert "filters" in call[2]

    @pytest.mark.asyncio
    async def test_events_with_since(self):
        transport = MockTransport()
        transport.register_stream("GET", "/events", [])
        since = datetime(2024, 1, 1)
        async with AsyncDockerClient(transport=transport) as docker:
            _ = [e async for e in docker.events(since=since)]
            call = transport.calls[0]
            assert "since" in call[2]

    @pytest.mark.asyncio
    async def test_events_with_until(self):
        transport = MockTransport()
        transport.register_stream("GET", "/events", [])
        until = datetime(2024, 12, 31)
        async with AsyncDockerClient(transport=transport) as docker:
            _ = [e async for e in docker.events(until=until)]
            call = transport.calls[0]
            assert "until" in call[2]

    @pytest.mark.asyncio
    async def test_events_empty(self):
        transport = MockTransport()
        transport.register_stream("GET", "/events", [])
        async with AsyncDockerClient(transport=transport) as docker:
            events = [e async for e in docker.events()]
            assert events == []

    @pytest.mark.asyncio
    async def test_multiple_events(self):
        transport = MockTransport()
        event1 = {**EVENT_FIXTURE, "Action": "start"}
        event2 = {**EVENT_FIXTURE, "Action": "stop"}
        chunks = [
            json.dumps(event1).encode() + b"\n",
            json.dumps(event2).encode() + b"\n",
        ]
        transport.register_stream("GET", "/events", chunks)
        async with AsyncDockerClient(transport=transport) as docker:
            events = [e async for e in docker.events()]
            assert len(events) == 2
            assert events[0].action == "start"
            assert events[1].action == "stop"


class TestMultipleClients:
    @pytest.mark.asyncio
    async def test_independent_clients(self):
        """Multiple clients with different transports coexist."""
        t1 = MockTransport()
        t2 = MockTransport()
        ctr = {"State": "running", "Created": 0, "Labels": {}, "Ports": []}
        t1.register(
            "GET",
            "/containers/json",
            [
                {"Id": "local1", "Names": ["/l"], "Image": "x", **ctr},
            ],
        )
        t2.register(
            "GET",
            "/containers/json",
            [
                {"Id": "remote1", "Names": ["/r"], "Image": "y", **ctr},
            ],
        )

        async with (
            AsyncDockerClient(transport=t1) as local,
            AsyncDockerClient(transport=t2) as remote,
        ):
            local_containers = await local.containers.list()
            remote_containers = await remote.containers.list()
            assert local_containers[0].id == "local1"
            assert remote_containers[0].id == "remote1"
