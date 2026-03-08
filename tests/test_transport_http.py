"""Tests for _BaseHTTPTransport and _check_response — HTTP-level behaviour."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from aiowhales.exceptions import (
    ConflictError,
    ContainerNotFound,
    DockerAPIError,
    TransportError,
)
from aiowhales.transport import _check_response

# UnixSocketTransport tests require Unix sockets (Linux/macOS)
unix_only = pytest.mark.skipif(sys.platform == "win32", reason="Unix sockets not available")

# -- helpers ------------------------------------------------------------------


def _fake_response(status: int = 200, text: str = "", content_type: str = "text/plain"):
    resp = AsyncMock(spec=aiohttp.ClientResponse)
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.content_type = content_type
    return resp


# -- _check_response tests ---------------------------------------------------


class TestCheckResponse:
    @pytest.mark.asyncio
    async def test_ok_status_does_nothing(self):
        resp = _fake_response(200)
        await _check_response(resp, "/containers/json")

    @pytest.mark.asyncio
    async def test_404_container_path_raises_container_not_found(self):
        resp = _fake_response(404, text="No such container")
        with pytest.raises(ContainerNotFound):
            await _check_response(resp, "/containers/abc/json")

    @pytest.mark.asyncio
    async def test_409_raises_conflict_error(self):
        resp = _fake_response(409, text="conflict")
        with pytest.raises(ConflictError):
            await _check_response(resp, "/containers/abc/stop")

    @pytest.mark.asyncio
    async def test_500_raises_docker_api_error(self):
        resp = _fake_response(500, text="server error")
        with pytest.raises(DockerAPIError) as exc_info:
            await _check_response(resp, "/info")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_399_does_not_raise(self):
        resp = _fake_response(399)
        await _check_response(resp, "/info")


# -- _BaseHTTPTransport via UnixSocketTransport (real session, mocked HTTP) ---


@unix_only
class TestBaseHTTPTransportGet:
    @pytest.mark.asyncio
    async def test_get_json_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, content_type="application/json")
        mock_resp.json = AsyncMock(return_value={"Id": "abc"})

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "get", return_value=cm):
            result = await transport.get("/containers/json")
        assert result == {"Id": "abc"}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_get_text_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, text="OK", content_type="text/plain")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "get", return_value=cm):
            result = await transport.get("/info")
        assert result == "OK"
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_get_transport_error_on_connect_failure(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with (
            patch.object(
                transport._session,
                "get",
                side_effect=aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            ),
            pytest.raises(TransportError),
        ):
            await transport.get("/info")
        await transport.aclose()


@unix_only
class TestBaseHTTPTransportPost:
    @pytest.mark.asyncio
    async def test_post_json_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, text='{"Id":"x"}', content_type="application/json")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post("/containers/create", {"Image": "nginx"})
        assert result == {"Id": "x"}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_empty_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(204, text="", content_type="text/plain")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post("/containers/abc/start")
        assert result == {}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_text_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, text="plain text", content_type="text/plain")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post("/info")
        assert result == "plain text"
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_transport_error(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with (
            patch.object(
                transport._session,
                "post",
                side_effect=aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            ),
            pytest.raises(TransportError),
        ):
            await transport.post("/containers/create")
        await transport.aclose()


@unix_only
class TestBaseHTTPTransportPostRaw:
    @pytest.mark.asyncio
    async def test_post_raw_json_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, text='{"stream":"ok"}', content_type="application/json")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post_raw("/build", data=b"tar-data")
        assert result == {"stream": "ok"}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_raw_empty_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(204, text="", content_type="text/plain")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post_raw("/build", data=b"tar-data")
        assert result == {}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_raw_text_response(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200, text="plain", content_type="text/plain")

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm):
            result = await transport.post_raw("/build", data=b"tar-data")
        assert result == "plain"
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_post_raw_transport_error(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with (
            patch.object(
                transport._session,
                "post",
                side_effect=aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            ),
            pytest.raises(TransportError),
        ):
            await transport.post_raw("/build")
        await transport.aclose()


@unix_only
class TestBaseHTTPTransportDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(204)

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "delete", return_value=cm):
            await transport.delete("/containers/abc")
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_delete_transport_error(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with (
            patch.object(
                transport._session,
                "delete",
                side_effect=aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            ),
            pytest.raises(TransportError),
        ):
            await transport.delete("/containers/abc")
        await transport.aclose()


@unix_only
class TestBaseHTTPTransportStream:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200)

        async def fake_iter_any():
            for chunk in [b"chunk1", b"chunk2"]:
                yield chunk

        mock_resp.content = MagicMock()
        mock_resp.content.iter_any = fake_iter_any

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "get", return_value=cm):
            chunks = [c async for c in transport.stream("GET", "/containers/abc/logs")]
        assert chunks == [b"chunk1", b"chunk2"]
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_stream_with_data_and_headers(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        mock_resp = _fake_response(200)

        async def fake_iter_any():
            yield b"data"

        mock_resp.content = MagicMock()
        mock_resp.content.iter_any = fake_iter_any

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(transport._session, "post", return_value=cm) as mock_post:
            chunks = [
                c
                async for c in transport.stream(
                    "POST",
                    "/exec/abc/start",
                    data=b"body",
                    headers={"Content-Type": "application/json"},
                )
            ]
            assert chunks == [b"data"]
            # Verify data and headers were passed
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["data"] == b"body"
            assert call_kwargs["headers"] == {"Content-Type": "application/json"}
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_stream_transport_error(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with (
            patch.object(
                transport._session,
                "get",
                side_effect=aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            ),
            pytest.raises(TransportError),
        ):
            _ = [c async for c in transport.stream("GET", "/containers/abc/logs")]
        await transport.aclose()


@unix_only
class TestBaseHTTPTransportAclose:
    @pytest.mark.asyncio
    async def test_aclose_closes_session(self):
        from aiowhales.transport import UnixSocketTransport

        transport = UnixSocketTransport()
        with patch.object(transport._session, "close", new_callable=AsyncMock) as mock_close:
            await transport.aclose()
            mock_close.assert_called_once()
