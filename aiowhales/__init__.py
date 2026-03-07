"""aiowhales — async-native Python library for interacting with Docker."""

from .client import AsyncDockerClient, from_env
from .exceptions import (
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
from .models import (
    BuildOutput,
    Container,
    ContainerStats,
    DockerEvent,
    ExecResult,
    Image,
    Network,
    PullProgress,
    PushProgress,
    Volume,
)

# Convenience alias
DockerClient = AsyncDockerClient

__all__ = [
    "AiowhalesError",
    "AsyncDockerClient",
    "BuildOutput",
    "ComposeError",
    "ConflictError",
    "Container",
    "ContainerNotFound",
    "ContainerStats",
    "DaemonConnectionRefused",
    "DaemonNotRunning",
    "DockerAPIError",
    "DockerClient",
    "DockerEvent",
    "ExecResult",
    "Image",
    "ImageNotFound",
    "Network",
    "NetworkNotFound",
    "PullProgress",
    "PushProgress",
    "TransportError",
    "Volume",
    "VolumeNotFound",
    "from_env",
]

__version__ = "0.1.0"
