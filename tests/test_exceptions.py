"""Tests for the exception hierarchy."""

import pytest

from aiowhales.exceptions import (
    AiowhalesError,
    ComposeError,
    ConflictError,
    ContainerNotFound,
    DaemonConnectionRefused,
    DaemonNotRunning,
    DockerAPIError,
    ImageNotFound,
    NetworkNotFound,
    TransportError,
    VolumeNotFound,
)


class TestExceptionHierarchy:
    """Verify the inheritance chain is correct."""

    def test_base_exception_is_exception(self):
        assert issubclass(AiowhalesError, Exception)

    def test_docker_api_error_inherits_base(self):
        assert issubclass(DockerAPIError, AiowhalesError)

    def test_not_found_exceptions_inherit_docker_api_error(self):
        for exc_cls in [ContainerNotFound, ImageNotFound, VolumeNotFound, NetworkNotFound]:
            assert issubclass(exc_cls, DockerAPIError)

    def test_conflict_error_inherits_docker_api_error(self):
        assert issubclass(ConflictError, DockerAPIError)

    def test_transport_error_inherits_base(self):
        assert issubclass(TransportError, AiowhalesError)

    def test_daemon_errors_inherit_transport_error(self):
        assert issubclass(DaemonNotRunning, TransportError)
        assert issubclass(DaemonConnectionRefused, TransportError)

    def test_compose_error_inherits_base(self):
        assert issubclass(ComposeError, AiowhalesError)


class TestDockerAPIError:
    def test_attributes(self):
        err = DockerAPIError(500, "Internal Server Error")
        assert err.status_code == 500
        assert err.message == "Internal Server Error"

    def test_str_representation(self):
        err = DockerAPIError(500, "Internal Server Error")
        assert "500" in str(err)
        assert "Internal Server Error" in str(err)

    def test_catchable_as_base(self):
        with pytest.raises(AiowhalesError):
            raise DockerAPIError(400, "bad request")


class TestNotFoundExceptions:
    def test_container_not_found_default_message(self):
        err = ContainerNotFound()
        assert err.status_code == 404
        assert "Container not found" in err.message

    def test_container_not_found_custom_message(self):
        err = ContainerNotFound("No such container: abc123")
        assert err.status_code == 404
        assert "abc123" in err.message

    def test_image_not_found(self):
        err = ImageNotFound()
        assert err.status_code == 404

    def test_volume_not_found(self):
        err = VolumeNotFound()
        assert err.status_code == 404

    def test_network_not_found(self):
        err = NetworkNotFound()
        assert err.status_code == 404

    def test_not_found_catchable_as_docker_api_error(self):
        with pytest.raises(DockerAPIError):
            raise ContainerNotFound()


class TestConflictError:
    def test_default_message(self):
        err = ConflictError()
        assert err.status_code == 409

    def test_custom_message(self):
        err = ConflictError("name already in use")
        assert "name already in use" in err.message


class TestComposeError:
    def test_attributes(self):
        err = ComposeError(1, "service 'web' failed to build")
        assert err.returncode == 1
        assert err.stderr == "service 'web' failed to build"

    def test_str_representation(self):
        err = ComposeError(2, "file not found")
        s = str(err)
        assert "exit 2" in s
        assert "file not found" in s

    def test_catchable_as_base(self):
        with pytest.raises(AiowhalesError):
            raise ComposeError(1, "failed")


class TestTransportErrors:
    def test_daemon_not_running(self):
        err = DaemonNotRunning("socket not found")
        assert isinstance(err, TransportError)
        assert isinstance(err, AiowhalesError)

    def test_daemon_connection_refused(self):
        err = DaemonConnectionRefused("connection refused")
        assert isinstance(err, TransportError)
