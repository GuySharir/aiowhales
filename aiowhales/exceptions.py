"""Exception hierarchy for aiowhales."""

from __future__ import annotations


class AiowhalesError(Exception):
    """Base exception for all aiowhales errors."""


class DockerAPIError(AiowhalesError):
    """Non-2xx HTTP response from the Docker daemon."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Docker API error {status_code}: {message}")


class ContainerNotFound(DockerAPIError):
    """404 on a container endpoint."""

    def __init__(self, message: str = "Container not found") -> None:
        super().__init__(404, message)


class ImageNotFound(DockerAPIError):
    """404 on an image endpoint."""

    def __init__(self, message: str = "Image not found") -> None:
        super().__init__(404, message)


class VolumeNotFound(DockerAPIError):
    """404 on a volume endpoint."""

    def __init__(self, message: str = "Volume not found") -> None:
        super().__init__(404, message)


class NetworkNotFound(DockerAPIError):
    """404 on a network endpoint."""

    def __init__(self, message: str = "Network not found") -> None:
        super().__init__(404, message)


class ConflictError(DockerAPIError):
    """409 — name conflict, etc."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(409, message)


class TransportError(AiowhalesError):
    """aiohttp connection failure."""


class DaemonNotRunning(TransportError):
    """Docker socket not found."""


class DaemonConnectionRefused(TransportError):
    """Connection to Docker daemon refused."""


class ComposeError(AiowhalesError):
    """Non-zero exit from the docker compose CLI."""

    def __init__(self, returncode: int, stderr: str) -> None:
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"docker compose failed (exit {returncode}): {stderr}")
