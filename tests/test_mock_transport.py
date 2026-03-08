"""Tests for MockTransport."""

import pytest

from aiowhales.testing import MockTransport


class TestMockTransport:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        t = MockTransport()
        t.register("GET", "/test", {"key": "value"})
        result = await t.get("/test")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_register_and_post(self):
        t = MockTransport()
        t.register("POST", "/test", {"created": True})
        result = await t.post("/test", {"data": "payload"})
        assert result == {"created": True}

    @pytest.mark.asyncio
    async def test_register_and_post_raw(self):
        t = MockTransport()
        t.register("POST", "/test", {"ok": True})
        result = await t.post_raw("/test", data=b"raw", headers={"Content-Type": "text/plain"})
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_delete_returns_none(self):
        t = MockTransport()
        result = await t.delete("/test")
        assert result is None

    @pytest.mark.asyncio
    async def test_unregistered_path_returns_empty_dict(self):
        t = MockTransport()
        result = await t.get("/nonexistent")
        assert result == {}

    @pytest.mark.asyncio
    async def test_calls_tracked(self):
        t = MockTransport()
        await t.get("/a", foo="bar")
        await t.post("/b", {"data": 1})
        await t.delete("/c")
        assert len(t.calls) == 3
        assert t.calls[0] == ("GET", "/a", {"foo": "bar"})
        assert t.calls[1] == ("POST", "/b", {})
        assert t.calls[2] == ("DELETE", "/c", {})

    @pytest.mark.asyncio
    async def test_stream_registered_chunks(self):
        t = MockTransport()
        t.register_stream("GET", "/logs", [b"chunk1", b"chunk2", b"chunk3"])
        chunks = [chunk async for chunk in t.stream("GET", "/logs")]
        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]

    @pytest.mark.asyncio
    async def test_stream_unregistered_returns_empty(self):
        t = MockTransport()
        chunks = [chunk async for chunk in t.stream("GET", "/logs")]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_calls_tracked(self):
        t = MockTransport()
        t.register_stream("GET", "/events", [b"data"])
        _ = [chunk async for chunk in t.stream("GET", "/events", filters="test")]
        assert len(t.calls) == 1
        assert t.calls[0] == ("GET", "/events", {"filters": "test"})

    @pytest.mark.asyncio
    async def test_case_insensitive_method(self):
        t = MockTransport()
        t.register("get", "/test", {"ok": True})
        result = await t.get("/test")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_prefix_match_for_versioned_paths(self):
        t = MockTransport()
        t.register("GET", "/containers/json", [{"Id": "abc"}])
        result = await t.get("/v1.43/containers/json")
        assert result == [{"Id": "abc"}]

    @pytest.mark.asyncio
    async def test_exact_match_takes_precedence(self):
        t = MockTransport()
        t.register("GET", "/test", {"source": "exact"})
        t.register("GET", "/longer/test", {"source": "prefix"})
        result = await t.get("/test")
        assert result["source"] == "exact"

    @pytest.mark.asyncio
    async def test_aclose_is_noop(self):
        t = MockTransport()
        await t.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_multiple_registrations_overwrite(self):
        t = MockTransport()
        t.register("GET", "/test", {"version": 1})
        t.register("GET", "/test", {"version": 2})
        result = await t.get("/test")
        assert result == {"version": 2}

    @pytest.mark.asyncio
    async def test_different_methods_same_path(self):
        t = MockTransport()
        t.register("GET", "/resource", {"action": "read"})
        t.register("POST", "/resource", {"action": "create"})
        get_result = await t.get("/resource")
        post_result = await t.post("/resource")
        assert get_result["action"] == "read"
        assert post_result["action"] == "create"
