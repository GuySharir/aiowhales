"""Image snapshot model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Image:
    """Immutable snapshot of a Docker image."""

    id: str
    tags: list[str]
    size: int
    created: datetime
    labels: dict[str, str]
    architecture: str
    os: str

    @property
    def short_id(self) -> str:
        return self.id[:12] if self.id.startswith("sha256:") else self.id[:12]


@dataclass(frozen=True)
class PullProgress:
    """Progress update during image pull."""

    status: str
    layer_id: str
    progress: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)


@dataclass(frozen=True)
class PushProgress:
    """Progress update during image push."""

    status: str
    layer_id: str
    progress: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)


@dataclass(frozen=True)
class BuildOutput:
    """A line of build output."""

    stream: str
    error: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)


def _parse_image(data: dict[str, Any]) -> Image:
    """Parse Docker API JSON into an Image snapshot."""
    created_raw = data.get("Created", "")
    if isinstance(created_raw, int):
        created = datetime.fromtimestamp(created_raw)
    elif isinstance(created_raw, str) and created_raw:
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created = datetime.min
    else:
        created = datetime.min

    tags = data.get("RepoTags") or []

    return Image(
        id=data.get("Id", ""),
        tags=tags,
        size=data.get("Size", 0),
        created=created,
        labels=data.get("Labels") or data.get("Config", {}).get("Labels") or {},
        architecture=data.get("Architecture", ""),
        os=data.get("Os", ""),
    )
