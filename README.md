# aiowhales

[![PyPI version](https://img.shields.io/pypi/v/aiowhales.svg)](https://pypi.org/project/aiowhales/)
[![Python versions](https://img.shields.io/pypi/pyversions/aiowhales.svg)](https://pypi.org/project/aiowhales/)
[![License](https://img.shields.io/pypi/l/aiowhales.svg)](https://github.com/GuySharir/aiowhales/blob/main/LICENSE)

Async-native Python library for interacting with Docker. Built on `aiohttp` and `asyncio`, `aiowhales` talks directly to the Docker Engine API over Unix sockets or TCP — no subprocess shells, no sync wrappers.

## Features

- **Fully async** — every operation is a native coroutine
- **Direct Docker API** — communicates over the Docker Engine REST API (Unix socket or TCP)
- **Typed models** — immutable dataclass snapshots for containers, images, volumes, networks
- **Streaming** — first-class `async for` support for logs, stats, pull progress, build output, and events
- **Compose** — async wrapper around `docker compose` CLI
- **Testable** — injectable transport layer with a built-in `MockTransport` for unit testing

## Installation

```bash
pip install aiowhales
```

## Quick Start

```python
import asyncio
from aiowhales import AsyncDockerClient

async def main():
    async with AsyncDockerClient() as docker:
        # Pull an image
        async for progress in docker.images.pull("python:3.12-slim"):
            print(progress.status)

        # Run a container
        container = await docker.containers.run(
            "python:3.12-slim",
            "python -c 'print(\"hello from aiowhales!\")'",
            detach=True,
        )

        # Wait and get logs
        await docker.containers.wait(container.id)
        async for line in docker.containers.logs(container.id):
            print(line)

        # Clean up
        await docker.containers.remove(container.id)

asyncio.run(main())
```

## Connecting to Docker

```python
from aiowhales import AsyncDockerClient, from_env

# Default — Unix socket at /var/run/docker.sock
async with AsyncDockerClient() as docker:
    ...

# Explicit Unix socket path
async with AsyncDockerClient("/var/run/docker.sock") as docker:
    ...

# TCP connection
async with AsyncDockerClient("tcp://192.168.1.100:2375") as docker:
    ...

# From DOCKER_HOST environment variable
docker = from_env()
```

## API Reference

### Containers

```python
# List all containers
containers = await docker.containers.list(all=True)

# Create and start
container = await docker.containers.run("nginx:latest", name="web", ports={"80/tcp": 8080})

# Lifecycle
await docker.containers.stop("container_id")
await docker.containers.start("container_id")
await docker.containers.restart("container_id")
await docker.containers.pause("container_id")
await docker.containers.unpause("container_id")

# Inspect
container = await docker.containers.get("container_id")
print(container.status, container.image)

# Execute a command
result = await docker.containers.exec_run("container_id", ["ls", "-la"])

# Stream logs
async for line in docker.containers.logs("container_id", follow=True):
    print(line)

# Resource stats
stats = await docker.containers.stats("container_id")
print(f"CPU: {stats.cpu_percent}%  Memory: {stats.memory_usage}")

# Remove
await docker.containers.remove("container_id", force=True)
```

### Images

```python
# List images
images = await docker.images.list()

# Pull with progress
async for progress in docker.images.pull("ubuntu:latest"):
    print(f"{progress.status} {progress.progress or ''}")

# Build from Dockerfile
async for output in docker.images.build(".", tags=["myapp:latest"]):
    print(output.stream)

# Tag and push
await docker.images.tag("myapp:latest", "registry.example.com/myapp:v1")
async for progress in docker.images.push("registry.example.com/myapp:v1"):
    print(progress.status)

# Remove
await docker.images.remove("myapp:latest")
```

### Volumes

```python
volumes = await docker.volumes.list()
vol = await docker.volumes.create("my-data", labels={"env": "dev"})
await docker.volumes.remove("my-data")
pruned = await docker.volumes.prune()
```

### Networks

```python
networks = await docker.networks.list()
net = await docker.networks.create("my-net", driver="bridge")
await docker.networks.connect(net.id, container.id, aliases=["web"])
await docker.networks.disconnect(net.id, container.id)
await docker.networks.remove(net.id)
```

### Exec

```python
# Run a command in a running container
result = await docker.exec.run("container_id", ["echo", "hello"])
print(result.exit_code, result.output)

# Stream output line by line
async for line in docker.exec.stream("container_id", ["tail", "-f", "/var/log/app.log"]):
    print(line)
```

### Compose

```python
# Start services
await docker.compose.up("./my-project", detach=True, build=True)

# List services
services = await docker.compose.ps("./my-project")

# View logs
async for line in docker.compose.logs("./my-project", service="web", follow=True):
    print(line)

# Stop and clean up
await docker.compose.down("./my-project", volumes=True)
```

### Events

```python
# Stream Docker engine events
async for event in docker.events(filters={"type": ["container"]}):
    print(f"{event.action} {event.actor_id}")
```

## Testing

aiowhales ships with a `MockTransport` for unit testing without a Docker daemon:

```python
import pytest
from aiowhales import AsyncDockerClient
from aiowhales.testing import MockTransport

@pytest.fixture
def docker():
    transport = MockTransport()
    transport.register("GET", "/containers/json", [
        {"Id": "abc123", "Names": ["/myapp"], "State": "running", "Image": "nginx"}
    ])
    return AsyncDockerClient(transport=transport)

async def test_list_containers(docker):
    containers = await docker.containers.list()
    assert len(containers) == 1
    assert containers[0].id == "abc123"
```

## Models

All models are **frozen dataclasses** — immutable snapshots of Docker state:

| Model | Description |
|---|---|
| `Container` | Container snapshot (id, name, status, image, ports, labels, ...) |
| `Image` | Image snapshot (id, tags, size, created) |
| `Volume` | Volume snapshot (name, driver, mountpoint, labels) |
| `Network` | Network snapshot (id, name, driver, containers) |
| `ContainerStats` | CPU/memory/network usage stats |
| `ExecResult` | Command execution result (exit_code, output) |
| `DockerEvent` | Engine event (action, type, actor_id, time) |
| `PullProgress` / `PushProgress` | Image transfer progress |
| `BuildOutput` | Build step output |

## Requirements

- Python 3.11+
- aiohttp >= 3.9
- Docker Engine API v1.43+

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
