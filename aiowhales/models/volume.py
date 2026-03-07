"""Volume snapshot model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Volume:
    """Immutable snapshot of a Docker volume."""

    name: str
    driver: str
    mountpoint: str
    labels: dict[str, str]
    created: datetime
    scope: str


def _parse_volume(data: dict[str, Any]) -> Volume:
    """Parse Docker API JSON into a Volume snapshot."""
    created_raw = data.get("CreatedAt", "")
    if isinstance(created_raw, str) and created_raw:
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created = datetime.min
    else:
        created = datetime.min

    return Volume(
        name=data.get("Name", ""),
        driver=data.get("Driver", ""),
        mountpoint=data.get("Mountpoint", ""),
        labels=data.get("Labels") or {},
        created=created,
        scope=data.get("Scope", ""),
    )
