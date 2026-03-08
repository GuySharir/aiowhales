"""Shared fixtures for aiowhales tests."""

from __future__ import annotations

import pytest

from aiowhales import AsyncDockerClient
from aiowhales.testing import MockTransport


@pytest.fixture
def transport():
    """A fresh MockTransport for each test."""
    return MockTransport()


@pytest.fixture
async def docker(transport):
    """An AsyncDockerClient backed by MockTransport."""
    async with AsyncDockerClient(transport=transport) as client:
        yield client


# -- Fixture data: realistic Docker API JSON responses --

CONTAINER_LIST_FIXTURE = [
    {
        "Id": "abc123def456",
        "Names": ["/web-app"],
        "Image": "nginx:latest",
        "State": "running",
        "Status": "Up 2 hours",
        "Created": 1700000000,
        "Labels": {"app": "web", "env": "prod"},
        "Ports": [
            {"PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"},
            {"PrivatePort": 443, "PublicPort": 8443, "Type": "tcp"},
        ],
    },
    {
        "Id": "789ghi012jkl",
        "Names": ["/db"],
        "Image": "postgres:15",
        "State": "running",
        "Status": "Up 1 hour",
        "Created": 1700003600,
        "Labels": {"app": "db"},
        "Ports": [{"PrivatePort": 5432, "PublicPort": 5432, "Type": "tcp"}],
    },
]

CONTAINER_INSPECT_FIXTURE = {
    "Id": "abc123def456",
    "Name": "/web-app",
    "Created": "2024-01-15T10:30:00.000000000Z",
    "State": {"Status": "running", "Running": True, "Pid": 1234},
    "Config": {
        "Image": "nginx:latest",
        "Labels": {"app": "web", "env": "prod"},
        "Env": ["FOO=bar", "DEBUG=1", "PATH=/usr/bin"],
    },
    "NetworkSettings": {
        "Ports": {
            "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}],
            "443/tcp": None,
        }
    },
}

CONTAINER_STOPPED_FIXTURE = {
    "Id": "stopped123",
    "Name": "/stopped-container",
    "Created": "2024-01-01T00:00:00Z",
    "State": {"Status": "exited", "Running": False, "ExitCode": 0},
    "Config": {
        "Image": "alpine:latest",
        "Labels": {},
        "Env": [],
    },
    "NetworkSettings": {"Ports": {}},
}

IMAGE_LIST_FIXTURE = [
    {
        "Id": "sha256:abc123",
        "RepoTags": ["nginx:latest", "nginx:1.25"],
        "Size": 187000000,
        "Created": 1700000000,
        "Labels": {"maintainer": "NGINX"},
    },
    {
        "Id": "sha256:def456",
        "RepoTags": ["python:3.12-slim"],
        "Size": 52000000,
        "Created": 1700100000,
        "Labels": {},
    },
]

IMAGE_INSPECT_FIXTURE = {
    "Id": "sha256:abc123full",
    "RepoTags": ["nginx:latest"],
    "Size": 187000000,
    "Created": "2024-01-15T00:00:00Z",
    "Labels": {"maintainer": "NGINX"},
    "Architecture": "amd64",
    "Os": "linux",
    "Config": {"Labels": {"maintainer": "NGINX"}},
}

VOLUME_LIST_FIXTURE = {
    "Volumes": [
        {
            "Name": "my-data",
            "Driver": "local",
            "Mountpoint": "/var/lib/docker/volumes/my-data/_data",
            "Labels": {"project": "myapp"},
            "CreatedAt": "2024-01-15T10:00:00Z",
            "Scope": "local",
        },
        {
            "Name": "db-data",
            "Driver": "local",
            "Mountpoint": "/var/lib/docker/volumes/db-data/_data",
            "Labels": {},
            "CreatedAt": "2024-01-14T08:00:00Z",
            "Scope": "local",
        },
    ]
}

VOLUME_INSPECT_FIXTURE = {
    "Name": "my-data",
    "Driver": "local",
    "Mountpoint": "/var/lib/docker/volumes/my-data/_data",
    "Labels": {"project": "myapp"},
    "CreatedAt": "2024-01-15T10:00:00Z",
    "Scope": "local",
}

NETWORK_LIST_FIXTURE = [
    {
        "Id": "net123",
        "Name": "bridge",
        "Driver": "bridge",
        "Scope": "local",
        "Labels": {},
        "Created": "2024-01-01T00:00:00Z",
    },
    {
        "Id": "net456",
        "Name": "my-network",
        "Driver": "bridge",
        "Scope": "local",
        "Labels": {"project": "myapp"},
        "Created": "2024-01-15T12:00:00Z",
    },
]

NETWORK_INSPECT_FIXTURE = {
    "Id": "net456",
    "Name": "my-network",
    "Driver": "bridge",
    "Scope": "local",
    "Labels": {"project": "myapp"},
    "Created": "2024-01-15T12:00:00Z",
}

STATS_FIXTURE = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 200000000},
        "system_cpu_usage": 1000000000,
        "online_cpus": 4,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 100000000},
        "system_cpu_usage": 500000000,
    },
    "memory_stats": {
        "usage": 104857600,  # 100 MB
        "limit": 2147483648,  # 2 GB
    },
    "networks": {
        "eth0": {"rx_bytes": 1024000, "tx_bytes": 512000},
        "eth1": {"rx_bytes": 256000, "tx_bytes": 128000},
    },
    "pids_stats": {"current": 5},
}

EVENT_FIXTURE = {
    "Type": "container",
    "Action": "start",
    "Actor": {
        "ID": "abc123",
        "Attributes": {"name": "web-app", "image": "nginx:latest"},
    },
    "time": 1700000000,
}
