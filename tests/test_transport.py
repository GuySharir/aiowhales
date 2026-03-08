"""Tests for transport layer — error mapping, protocol compliance."""

import sys

import pytest

from aiowhales.exceptions import (
    ContainerNotFound,
    DockerAPIError,
    ImageNotFound,
    NetworkNotFound,
    VolumeNotFound,
)
from aiowhales.testing import MockTransport
from aiowhales.transport import (
    AbstractTransport,
    TCPTransport,
    UnixSocketTransport,
    _not_found_exception,
    _versioned,
)


class TestVersionedPath:
    def test_adds_version_prefix(self):
        assert _versioned("/containers/json") == "/v1.43/containers/json"

    def test_preserves_path(self):
        result = _versioned("/images/sha256:abc/json")
        assert result.endswith("/images/sha256:abc/json")
        assert result.startswith("/v1.43")


class TestNotFoundExceptionMapping:
    def test_container_path(self):
        exc = _not_found_exception("/containers/abc/json", "not found")
        assert isinstance(exc, ContainerNotFound)

    def test_image_path(self):
        exc = _not_found_exception("/images/nginx/json", "not found")
        assert isinstance(exc, ImageNotFound)

    def test_volume_path(self):
        exc = _not_found_exception("/volumes/mydata", "not found")
        assert isinstance(exc, VolumeNotFound)

    def test_network_path(self):
        exc = _not_found_exception("/networks/bridge", "not found")
        assert isinstance(exc, NetworkNotFound)

    def test_unknown_path(self):
        exc = _not_found_exception("/unknown/resource", "not found")
        assert isinstance(exc, DockerAPIError)
        assert exc.status_code == 404

    def test_message_preserved(self):
        exc = _not_found_exception("/containers/abc", "No such container: abc")
        assert "No such container: abc" in exc.message


class TestAbstractTransportProtocol:
    def test_mock_transport_satisfies_protocol(self):
        """MockTransport should satisfy the AbstractTransport protocol."""
        transport = MockTransport()
        assert isinstance(transport, AbstractTransport)


@pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")
class TestUnixSocketTransport:
    @pytest.mark.asyncio
    async def test_default_socket_path(self):
        transport = UnixSocketTransport()
        assert transport.socket_path == "/var/run/docker.sock"
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_custom_socket_path(self):
        transport = UnixSocketTransport("/run/user/1000/docker.sock")
        assert transport.socket_path == "/run/user/1000/docker.sock"
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_has_session(self):
        transport = UnixSocketTransport()
        assert transport._session is not None
        await transport.aclose()


class TestTCPTransport:
    @pytest.mark.asyncio
    async def test_has_session(self):
        transport = TCPTransport("http://localhost:2375")
        assert transport._session is not None
        await transport.aclose()
