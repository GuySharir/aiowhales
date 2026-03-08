# Contributing to aiowhales

Thanks for your interest in contributing!

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Clone the repo
git clone https://github.com/GuySharir/aiowhales.git
cd aiowhales

# Install dependencies (creates .venv automatically)
uv sync
```

## Running Tests

```bash
# Run all unit tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_containers_api.py
```

All tests use `MockTransport` and do **not** require a running Docker daemon.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix
uv run ruff check --fix .

# Format
uv run ruff format .
```

## Type Checking

```bash
uv run mypy aiowhales --ignore-missing-imports
```

## Submitting Changes

1. Fork the repo and create a feature branch from `main`
2. Make your changes
3. Add or update tests as needed
4. Ensure `pytest`, `ruff check .`, and `ruff format --check .` all pass
5. Open a pull request against `main`

## Project Structure

```
aiowhales/
├── __init__.py          # Public API exports
├── client.py            # AsyncDockerClient entry point
├── transport.py         # HTTP transport (Unix socket / TCP)
├── stream.py            # Log demuxing and JSON streaming
├── exceptions.py        # Exception hierarchy
├── testing.py           # MockTransport for unit tests
├── api/                 # API namespace modules
│   ├── containers.py
│   ├── images.py
│   ├── volumes.py
│   ├── networks.py
│   ├── exec.py
│   └── compose.py
└── models/              # Immutable dataclass models
    ├── container.py
    ├── image.py
    ├── volume.py
    ├── network.py
    ├── events.py
    └── exec_result.py
```
