"""Network snapshot model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Network:
    """Immutable snapshot of a Docker network."""

    id: str
    name: str
    driver: str
    scope: str
    labels: dict[str, str]
    created: datetime


def _parse_network(data: dict[str, Any]) -> Network:
    """Parse Docker API JSON into a Network snapshot."""
    created_raw = data.get("Created", "")
    if isinstance(created_raw, str) and created_raw:
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created = datetime.min
    else:
        created = datetime.min

    return Network(
        id=data.get("Id", ""),
        name=data.get("Name", ""),
        driver=data.get("Driver", ""),
        scope=data.get("Scope", ""),
        labels=data.get("Labels") or {},
        created=created,
    )
