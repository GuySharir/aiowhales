# Contributing to aiowhales

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/GuySharir/aiowhales.git
cd aiowhales

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Running Tests

```bash
# Run all unit tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_containers_api.py
```

All tests use `MockTransport` and do **not** require a running Docker daemon.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix
ruff check --fix .

# Format
ruff format .
```

## Type Checking

```bash
mypy aiowhales --ignore-missing-imports
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
