"""Tests for stream helpers — demuxing, decoding, JSON parsing."""

import json
import struct

import pytest

from aiowhales.stream import LogLine, decode_stream, demux_log_stream, json_stream


async def _async_iter(chunks: list[bytes]):
    """Helper to create an AsyncIterator from a list of byte chunks."""
    for chunk in chunks:
        yield chunk


def _make_docker_frame(stream_type: int, payload: bytes) -> bytes:
    """Build a Docker log frame: [type, 0, 0, 0, size(4 bytes BE), payload]."""
    header = struct.pack(">BxxxI", stream_type, len(payload))
    return header + payload


class TestLogLine:
    def test_frozen(self):
        line = LogLine(text="hello", stream="stdout")
        with pytest.raises(AttributeError):
            line.text = "world"

    def test_equality(self):
        a = LogLine(text="hello", stream="stdout")
        b = LogLine(text="hello", stream="stdout")
        assert a == b

    def test_inequality_text(self):
        a = LogLine(text="hello", stream="stdout")
        b = LogLine(text="world", stream="stdout")
        assert a != b

    def test_inequality_stream(self):
        a = LogLine(text="hello", stream="stdout")
        b = LogLine(text="hello", stream="stderr")
        assert a != b


class TestDemuxLogStream:
    @pytest.mark.asyncio
    async def test_single_stdout_frame(self):
        frame = _make_docker_frame(1, b"hello world\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 1
        assert lines[0].text == "hello world"
        assert lines[0].stream == "stdout"

    @pytest.mark.asyncio
    async def test_single_stderr_frame(self):
        frame = _make_docker_frame(2, b"error occurred\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 1
        assert lines[0].text == "error occurred"
        assert lines[0].stream == "stderr"

    @pytest.mark.asyncio
    async def test_mixed_stdout_stderr(self):
        frames = (
            _make_docker_frame(1, b"output line\n")
            + _make_docker_frame(2, b"error line\n")
            + _make_docker_frame(1, b"more output\n")
        )
        lines = [line async for line in demux_log_stream(_async_iter([frames]))]
        assert len(lines) == 3
        assert lines[0] == LogLine(text="output line", stream="stdout")
        assert lines[1] == LogLine(text="error line", stream="stderr")
        assert lines[2] == LogLine(text="more output", stream="stdout")

    @pytest.mark.asyncio
    async def test_split_across_chunks(self):
        """Frame split across multiple network chunks."""
        frame = _make_docker_frame(1, b"hello world\n")
        mid = len(frame) // 2
        chunk1 = frame[:mid]
        chunk2 = frame[mid:]
        lines = [line async for line in demux_log_stream(_async_iter([chunk1, chunk2]))]
        assert len(lines) == 1
        assert lines[0].text == "hello world"

    @pytest.mark.asyncio
    async def test_multiple_frames_in_single_chunk(self):
        frame1 = _make_docker_frame(1, b"line1\n")
        frame2 = _make_docker_frame(1, b"line2\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame1 + frame2]))]
        assert len(lines) == 2
        assert lines[0].text == "line1"
        assert lines[1].text == "line2"

    @pytest.mark.asyncio
    async def test_empty_payload_skipped(self):
        frame = _make_docker_frame(1, b"\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 0

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        lines = [line async for line in demux_log_stream(_async_iter([]))]
        assert lines == []

    @pytest.mark.asyncio
    async def test_unknown_stream_type_defaults_to_stdout(self):
        frame = _make_docker_frame(99, b"unknown\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 1
        assert lines[0].stream == "stdout"

    @pytest.mark.asyncio
    async def test_utf8_content(self):
        frame = _make_docker_frame(1, "héllo wörld 🐳\n".encode("utf-8"))
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert lines[0].text == "héllo wörld 🐳"

    @pytest.mark.asyncio
    async def test_invalid_utf8_replaced(self):
        frame = _make_docker_frame(1, b"hello \xff\xfe world\n")
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 1
        assert "hello" in lines[0].text

    @pytest.mark.asyncio
    async def test_large_payload(self):
        payload = b"x" * 100000 + b"\n"
        frame = _make_docker_frame(1, payload)
        lines = [line async for line in demux_log_stream(_async_iter([frame]))]
        assert len(lines) == 1
        assert len(lines[0].text) == 100000

    @pytest.mark.asyncio
    async def test_header_split_at_every_byte(self):
        """Ensure the demuxer handles the header arriving byte by byte."""
        frame = _make_docker_frame(1, b"test\n")
        chunks = [frame[i : i + 1] for i in range(len(frame))]
        lines = [line async for line in demux_log_stream(_async_iter(chunks))]
        assert len(lines) == 1
        assert lines[0].text == "test"


class TestDecodeStream:
    @pytest.mark.asyncio
    async def test_single_line(self):
        lines = [line async for line in decode_stream(_async_iter([b"hello\n"]))]
        assert lines == ["hello"]

    @pytest.mark.asyncio
    async def test_multiple_lines(self):
        lines = [line async for line in decode_stream(_async_iter([b"line1\nline2\nline3\n"]))]
        assert lines == ["line1", "line2", "line3"]

    @pytest.mark.asyncio
    async def test_no_trailing_newline(self):
        lines = [line async for line in decode_stream(_async_iter([b"no newline"]))]
        assert lines == ["no newline"]

    @pytest.mark.asyncio
    async def test_split_across_chunks(self):
        lines = [line async for line in decode_stream(_async_iter([b"hel", b"lo\nwor", b"ld\n"]))]
        assert lines == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        lines = [line async for line in decode_stream(_async_iter([]))]
        assert lines == []

    @pytest.mark.asyncio
    async def test_empty_lines(self):
        lines = [line async for line in decode_stream(_async_iter([b"\n\n\n"]))]
        assert lines == ["", "", ""]

    @pytest.mark.asyncio
    async def test_utf8_decoding(self):
        lines = [line async for line in decode_stream(_async_iter(["café\n".encode("utf-8")]))]
        assert lines == ["café"]


class TestJsonStream:
    @pytest.mark.asyncio
    async def test_single_json_object(self):
        data = json.dumps({"status": "pulling"}).encode() + b"\n"
        items = [item async for item in json_stream(_async_iter([data]))]
        assert len(items) == 1
        assert items[0] == {"status": "pulling"}

    @pytest.mark.asyncio
    async def test_multiple_json_objects(self):
        lines = [
            json.dumps({"id": 1}).encode() + b"\n",
            json.dumps({"id": 2}).encode() + b"\n",
        ]
        items = [item async for item in json_stream(_async_iter(lines))]
        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_blank_lines_skipped(self):
        data = b'{"a": 1}\n\n\n{"b": 2}\n'
        items = [item async for item in json_stream(_async_iter([data]))]
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_split_json_across_chunks(self):
        obj = json.dumps({"key": "value"}).encode() + b"\n"
        mid = len(obj) // 2
        items = [item async for item in json_stream(_async_iter([obj[:mid], obj[mid:]]))]
        assert len(items) == 1
        assert items[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        items = [item async for item in json_stream(_async_iter([]))]
        assert items == []

    @pytest.mark.asyncio
    async def test_nested_json(self):
        obj = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        data = json.dumps(obj).encode() + b"\n"
        items = [item async for item in json_stream(_async_iter([data]))]
        assert items[0] == obj
