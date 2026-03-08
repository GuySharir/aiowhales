<div align="center">

# 🐳 aiowhales

**The async Docker client for Python.**

Talk to Docker the way Python was meant to — with `async` and `await`.

[![CI](https://github.com/GuySharir/aiowhales/actions/workflows/ci.yml/badge.svg)](https://github.com/GuySharir/aiowhales/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/aiowhales.svg)](https://pypi.org/project/aiowhales/)
[![Python versions](https://img.shields.io/pypi/pyversions/aiowhales.svg)](https://pypi.org/project/aiowhales/)
[![Downloads](https://img.shields.io/pypi/dm/aiowhales.svg)](https://pypi.org/project/aiowhales/)
[![License](https://img.shields.io/pypi/l/aiowhales.svg)](https://github.com/GuySharir/aiowhales/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen)](https://github.com/GuySharir/aiowhales)
[![Typed](https://img.shields.io/badge/typed-mypy-blue)](https://github.com/GuySharir/aiowhales)

</div>

---

Built on `aiohttp`, `aiowhales` talks directly to the Docker Engine API over Unix sockets or TCP. No subprocess shells. No sync wrappers. No blocking threads. Just pure async Python.

```python
async with AsyncDockerClient() as docker:
    container = await docker.containers.run("python:3.13-slim", "echo hello!", detach=True)
    async for line in docker.containers.logs(container.id):
        print(line)  # hello!
```

## Why aiowhales?

| | aiowhales | docker-py | subprocess |
|---|---|---|---|
| Async native | ✅ | ❌ | ❌ |
| Direct API (no CLI) | ✅ | ✅ | ❌ |
| Typed models | ✅ | ❌ | ❌ |
| Streaming (`async for`) | ✅ | ❌ | ❌ |
| Built-in test mocks | ✅ | ❌ | ❌ |
| Cross-platform | ✅ | ✅ | ✅ |

## Install

```bash
pip install aiowhales
```

```bash
uv add aiowhales
```

## Quick Start

```python
import asyncio
from aiowhales import AsyncDockerClient

async def main():
    async with AsyncDockerClient() as docker:
        # Pull an image with streaming progress
        async for progress in docker.images.pull("python:3.12-slim"):
            print(progress.status)

        # Run a container
        container = await docker.containers.run(
            "python:3.12-slim",
            "python -c 'print(\"hello from aiowhales!\")'",
            detach=True,
        )

        # Stream logs
        await docker.containers.wait(container.id)
        async for line in docker.containers.logs(container.id):
            print(line)

        # Clean up
        await docker.containers.remove(container.id)

asyncio.run(main())
```

## Features

### 🔌 Connecting

```python
from aiowhales import AsyncDockerClient, from_env

# Unix socket (default on Linux/macOS)
async with AsyncDockerClient() as docker: ...

# TCP (default on Windows, or remote hosts)
async with AsyncDockerClient("tcp://192.168.1.100:2375") as docker: ...

# From DOCKER_HOST env var
docker = from_env()
```

### 📦 Containers

```python
# List
containers = await docker.containers.list(all=True)

# Run
container = await docker.containers.run("nginx:latest", name="web", ports={"80/tcp": 8080})

# Lifecycle
await docker.containers.stop(container.id)
await docker.containers.start(container.id)
await docker.containers.restart(container.id)

# Inspect
info = await docker.containers.get(container.id)
print(info.status, info.image)

# Exec into a running container
result = await docker.containers.exec_run(container.id, ["ls", "-la"])

# Stream logs in real time
async for line in docker.containers.logs(container.id, follow=True):
    print(line)

# Live resource stats
stats = await docker.containers.stats(container.id)
print(f"CPU: {stats.cpu_percent}%  Memory: {stats.memory_usage}")

# Remove
await docker.containers.remove(container.id, force=True)
```

### 🖼️ Images

```python
# List
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

### 💾 Volumes

```python
volumes = await docker.volumes.list()
vol = await docker.volumes.create("my-data", labels={"env": "dev"})
await docker.volumes.remove("my-data")
pruned = await docker.volumes.prune()
```

### 🌐 Networks

```python
networks = await docker.networks.list()
net = await docker.networks.create("my-net", driver="bridge")
await docker.networks.connect(net.id, container.id, aliases=["web"])
await docker.networks.disconnect(net.id, container.id)
await docker.networks.remove(net.id)
```

### ⚡ Exec

```python
# Run a command inside a container
result = await docker.exec.run(container.id, ["echo", "hello"])
print(result.exit_code, result.output)

# Stream output
async for line in docker.exec.stream(container.id, ["tail", "-f", "/var/log/app.log"]):
    print(line)
```

### 🎼 Compose

```python
await docker.compose.up("./my-project", detach=True, build=True)
services = await docker.compose.ps("./my-project")

async for line in docker.compose.logs("./my-project", service="web", follow=True):
    print(line)

await docker.compose.down("./my-project", volumes=True)
```

### 📡 Events

```python
async for event in docker.events(filters={"type": ["container"]}):
    print(f"{event.action} {event.actor_id}")
```

## Testing

aiowhales ships with `MockTransport` — test your Docker code without a running daemon:

```python
from aiowhales import AsyncDockerClient
from aiowhales.testing import MockTransport

transport = MockTransport()
transport.register("GET", "/containers/json", [
    {"Id": "abc123", "Names": ["/myapp"], "State": "running",
     "Image": "nginx", "Created": 0, "Labels": {}, "Ports": []}
])

async with AsyncDockerClient(transport=transport) as docker:
    containers = await docker.containers.list()
    assert containers[0].id == "abc123"
```

## Models

All models are **frozen dataclasses** — immutable snapshots of Docker state:

| Model | What it represents |
|---|---|
| `Container` | Container state — id, name, status, image, ports, labels |
| `Image` | Image metadata — id, tags, size, created |
| `Volume` | Volume info — name, driver, mountpoint, labels |
| `Network` | Network info — id, name, driver, connected containers |
| `ContainerStats` | Live CPU / memory / network usage |
| `ExecResult` | Command result — exit code + output |
| `DockerEvent` | Engine event — action, type, actor, timestamp |
| `PullProgress` / `PushProgress` | Image transfer progress |
| `BuildOutput` | Build step output |

## Platform Support

| Platform | Transport | Status |
|---|---|---|
| Linux | Unix socket | ✅ Fully supported |
| macOS | Unix socket | ✅ Fully supported |
| Windows | TCP (Docker Desktop) | ✅ Fully supported |

## Requirements

- **Python** 3.11+
- **aiohttp** >= 3.9
- **Docker Engine API** v1.43+

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
