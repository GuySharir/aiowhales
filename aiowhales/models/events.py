"""Docker event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DockerEvent:
    """A single Docker engine event."""

    type: str
    action: str
    actor_id: str
    actor_attributes: dict[str, str]
    time: datetime
    raw: dict[str, Any] = field(repr=False)


def _parse_event(data: dict[str, Any]) -> DockerEvent:
    """Parse a Docker event JSON object."""
    actor = data.get("Actor", {})
    ts = data.get("time", 0)
    time = datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.min

    return DockerEvent(
        type=data.get("Type", ""),
        action=data.get("Action", ""),
        actor_id=actor.get("ID", ""),
        actor_attributes=actor.get("Attributes", {}),
        time=time,
        raw=data,
    )
