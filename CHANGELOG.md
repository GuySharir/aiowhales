# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-08

### Added

- `AsyncDockerClient` with async context manager and `from_env()` factory
- **Containers API** — list, create, run, start, stop, restart, pause, unpause, rename, wait, remove, logs (streaming), stats, exec_run
- **Images API** — list, get, inspect, remove, tag, pull (streaming progress), push (streaming progress), build (streaming output)
- **Volumes API** — list, get, create, remove, prune
- **Networks API** — list, get, create, remove, connect, disconnect, prune
- **Exec API** — create, start, inspect, run, stream
- **Compose API** — up, down, ps, run, logs, build, pull, restart (wraps `docker compose` CLI)
- **Events** — stream Docker engine events with filtering
- Unix socket and TCP transport backends via aiohttp
- Typed immutable dataclass models: `Container`, `Image`, `Volume`, `Network`, `ContainerStats`, `ExecResult`, `DockerEvent`, `PullProgress`, `PushProgress`, `BuildOutput`
- Rich exception hierarchy: `DockerAPIError`, `ContainerNotFound`, `ImageNotFound`, `VolumeNotFound`, `NetworkNotFound`, `ConflictError`, `DaemonNotRunning`, `DaemonConnectionRefused`, `TransportError`, `ComposeError`
- `MockTransport` testing utility for unit tests without a Docker daemon
- PEP 561 `py.typed` marker
