"""Async stream helpers and Docker log demuxer."""

from __future__ import annotations

import struct
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogLine:
    """A single line from a Docker log stream."""

    text: str
    stream: str  # 'stdout' or 'stderr'


STREAM_TYPES = {0: "stdin", 1: "stdout", 2: "stderr"}


async def demux_log_stream(raw_stream: AsyncIterator[bytes]) -> AsyncIterator[LogLine]:
    """Demux a Docker multiplexed log stream into LogLine objects.

    Docker multiplexes stdout and stderr using an 8-byte frame header:
    - byte 0: stream type (1=stdout, 2=stderr)
    - bytes 1-3: padding
    - bytes 4-7: frame size (big-endian uint32)
    """
    buffer = b""
    async for chunk in raw_stream:
        buffer += chunk
        while len(buffer) >= 8:
            stream_type = buffer[0]
            frame_size = struct.unpack(">I", buffer[4:8])[0]
            if len(buffer) < 8 + frame_size:
                break
            payload = buffer[8 : 8 + frame_size]
            buffer = buffer[8 + frame_size :]
            stream_name = STREAM_TYPES.get(stream_type, "stdout")
            text = payload.decode("utf-8", errors="replace").rstrip("\n")
            if text:
                yield LogLine(text=text, stream=stream_name)


async def decode_stream(raw_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
    """Decode a raw byte stream into strings, splitting on newlines."""
    buffer = b""
    async for chunk in raw_stream:
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode("utf-8", errors="replace")
    if buffer:
        yield buffer.decode("utf-8", errors="replace")


async def json_stream(raw_stream: AsyncIterator[bytes]) -> AsyncIterator[dict[str, Any]]:
    """Parse a newline-delimited JSON stream."""
    import json

    async for line in decode_stream(raw_stream):
        line = line.strip()
        if line:
            yield json.loads(line)
