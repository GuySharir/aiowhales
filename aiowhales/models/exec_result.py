"""Exec result model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecResult:
    """Result of executing a command in a container."""

    exit_code: int
    output: str
