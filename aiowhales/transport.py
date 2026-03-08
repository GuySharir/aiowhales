"""Transport layer — raw HTTP over Unix socket or TCP."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

import aiohttp

from .exceptions import (
    ConflictError,
    ContainerNotFound,
    DockerAPIError,
    ImageNotFound,
    NetworkNotFound,
    TransportError,
    VolumeNotFound,
)

API_VERSION = "v1.43"


def _versioned(path: str) -> str:
    return f"/{API_VERSION}{path}"


_NOT_FOUND_MAP: dict[str, type] = {
    "/containers/": ContainerNotFound,
    "/images/": ImageNotFound,
    "/volumes/": VolumeNotFound,
    "/networks/": NetworkNotFound,
}


def _not_found_exception(path: str, message: str) -> DockerAPIError:
    for prefix, exc_cls in _NOT_FOUND_MAP.items():
        if prefix in path:
            exc: DockerAPIError = exc_cls(message)
            return exc
    return DockerAPIError(404, message)


async def _check_response(resp: aiohttp.ClientResponse, path: str) -> None:
    if resp.status < 400:
        return
    body = await resp.text()
    if resp.status == 404:
        raise _not_found_exception(path, body)
    if resp.status == 409:
        raise ConflictError(body)
    raise DockerAPIError(resp.status, body)


@runtime_checkable
class AbstractTransport(Protocol):
    async def get(self, path: str, **params: Any) -> Any: ...
    async def post(self, path: str, body: dict[str, Any] | None = None, **params: Any) -> Any: ...
    async def post_raw(
        self,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        **params: Any,
    ) -> Any: ...
    async def delete(self, path: str, **params: Any) -> None: ...
    async def stream(
        self,
        method: str,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        **params: Any,
    ) -> AsyncIterator[bytes]: ...
    async def aclose(self) -> None: ...


class _BaseHTTPTransport:
    """Shared implementation for Unix socket and TCP transports."""

    _session: aiohttp.ClientSession

    async def get(self, path: str, **params: Any) -> Any:
        url = _versioned(path)
        try:
            async with self._session.get(url, params=params or None) as resp:
                await _check_response(resp, path)
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except aiohttp.ClientConnectorError as exc:
            raise TransportError(str(exc)) from exc

    async def post(self, path: str, body: dict[str, Any] | None = None, **params: Any) -> Any:
        url = _versioned(path)
        try:
            async with self._session.post(url, json=body, params=params or None) as resp:
                await _check_response(resp, path)
                text = await resp.text()
                if not text:
                    return {}
                if resp.content_type == "application/json":
                    return json.loads(text)
                return text
        except aiohttp.ClientConnectorError as exc:
            raise TransportError(str(exc)) from exc

    async def post_raw(
        self,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        **params: Any,
    ) -> Any:
        url = _versioned(path)
        try:
            async with self._session.post(
                url,
                data=data,
                headers=headers,
                params=params or None,
            ) as resp:
                await _check_response(resp, path)
                text = await resp.text()
                if not text:
                    return {}
                if resp.content_type == "application/json":
                    return json.loads(text)
                return text
        except aiohttp.ClientConnectorError as exc:
            raise TransportError(str(exc)) from exc

    async def delete(self, path: str, **params: Any) -> None:
        url = _versioned(path)
        try:
            async with self._session.delete(url, params=params or None) as resp:
                await _check_response(resp, path)
        except aiohttp.ClientConnectorError as exc:
            raise TransportError(str(exc)) from exc

    async def stream(
        self,
        method: str,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
        **params: Any,
    ) -> AsyncIterator[bytes]:
        url = _versioned(path)
        try:
            meth = getattr(self._session, method.lower())
            kwargs: dict[str, Any] = {"params": params or None}
            if data is not None:
                kwargs["data"] = data
            if headers is not None:
                kwargs["headers"] = headers
            async with meth(url, **kwargs) as resp:
                await _check_response(resp, path)
                async for chunk in resp.content.iter_any():
                    yield chunk
        except aiohttp.ClientConnectorError as exc:
            raise TransportError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._session.close()


class UnixSocketTransport(_BaseHTTPTransport):
    """Transport over a Unix domain socket."""

    def __init__(self, socket_path: str = "/var/run/docker.sock") -> None:
        self.socket_path = socket_path
        connector = aiohttp.UnixConnector(path=socket_path)
        self._session = aiohttp.ClientSession(
            base_url="http://localhost",
            connector=connector,
        )


class TCPTransport(_BaseHTTPTransport):
    """Transport over TCP (with optional TLS)."""

    def __init__(self, base_url: str, ssl: Any = None) -> None:
        connector = aiohttp.TCPConnector(ssl=ssl)
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            connector=connector,
        )
