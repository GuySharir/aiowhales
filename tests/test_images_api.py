"""Tests for ImagesAPI."""

import json

import pytest

from aiowhales.api.images import ImagesAPI
from aiowhales.models.image import Image, PullProgress
from aiowhales.testing import MockTransport

from .conftest import IMAGE_INSPECT_FIXTURE, IMAGE_LIST_FIXTURE


@pytest.fixture
def api():
    transport = MockTransport()
    return ImagesAPI(transport), transport


class TestImagesList:
    @pytest.mark.asyncio
    async def test_list_returns_images(self, api):
        images_api, transport = api
        transport.register("GET", "/images/json", IMAGE_LIST_FIXTURE)
        result = await images_api.list()
        assert len(result) == 2
        assert all(isinstance(img, Image) for img in result)

    @pytest.mark.asyncio
    async def test_list_image_tags(self, api):
        images_api, transport = api
        transport.register("GET", "/images/json", IMAGE_LIST_FIXTURE)
        result = await images_api.list()
        assert result[0].tags == ["nginx:latest", "nginx:1.25"]
        assert result[1].tags == ["python:3.12-slim"]

    @pytest.mark.asyncio
    async def test_list_all_param(self, api):
        images_api, transport = api
        transport.register("GET", "/images/json", [])
        await images_api.list(all=True)
        assert transport.calls[0][2].get("all") == "true"

    @pytest.mark.asyncio
    async def test_list_empty(self, api):
        images_api, transport = api
        transport.register("GET", "/images/json", [])
        result = await images_api.list()
        assert result == []


class TestImagesGet:
    @pytest.mark.asyncio
    async def test_get_by_name(self, api):
        images_api, transport = api
        transport.register("GET", "/images/nginx:latest/json", IMAGE_INSPECT_FIXTURE)
        img = await images_api.get("nginx:latest")
        assert img.id == "sha256:abc123full"
        assert img.architecture == "amd64"
        assert img.os == "linux"

    @pytest.mark.asyncio
    async def test_inspect_alias(self, api):
        images_api, transport = api
        transport.register("GET", "/images/nginx/json", IMAGE_INSPECT_FIXTURE)
        img = await images_api.inspect("nginx")
        assert img.id == "sha256:abc123full"


class TestImagesRemove:
    @pytest.mark.asyncio
    async def test_remove(self, api):
        images_api, transport = api
        await images_api.remove("nginx:latest")
        assert transport.calls[0] == ("DELETE", "/images/nginx:latest", {})

    @pytest.mark.asyncio
    async def test_remove_force(self, api):
        images_api, transport = api
        await images_api.remove("nginx:latest", force=True)
        assert transport.calls[0][2].get("force") == "true"


class TestImagesTag:
    @pytest.mark.asyncio
    async def test_tag_with_repo_and_tag(self, api):
        images_api, transport = api
        transport.register("POST", "/images/nginx:latest/tag", {})
        await images_api.tag("nginx:latest", "myrepo:v1")
        call = transport.calls[0]
        assert call[2]["repo"] == "myrepo"
        assert call[2]["tag"] == "v1"

    @pytest.mark.asyncio
    async def test_tag_without_tag(self, api):
        images_api, transport = api
        transport.register("POST", "/images/nginx:latest/tag", {})
        await images_api.tag("nginx:latest", "myrepo")
        call = transport.calls[0]
        assert call[2]["repo"] == "myrepo"
        assert "tag" not in call[2]


class TestImagesPull:
    @pytest.mark.asyncio
    async def test_pull_with_tag(self, api):
        images_api, transport = api
        progress_data = [
            json.dumps({"status": "Pulling from library/nginx", "id": "latest"}).encode() + b"\n",
            json.dumps({"status": "Downloading", "id": "abc123", "progress": "50%"}).encode()
            + b"\n",
            json.dumps({"status": "Pull complete", "id": "abc123"}).encode() + b"\n",
        ]
        transport.register_stream("POST", "/images/create", progress_data)
        items = [item async for item in images_api.pull("nginx:1.25")]
        assert len(items) == 3
        assert all(isinstance(p, PullProgress) for p in items)
        assert items[1].status == "Downloading"
        assert items[1].layer_id == "abc123"
        assert items[1].progress == "50%"

    @pytest.mark.asyncio
    async def test_pull_default_latest(self, api):
        images_api, transport = api
        transport.register_stream("POST", "/images/create", [])
        _ = [item async for item in images_api.pull("nginx")]
        call = transport.calls[0]
        assert call[2].get("tag") == "latest"

    @pytest.mark.asyncio
    async def test_pull_empty_stream(self, api):
        images_api, transport = api
        transport.register_stream("POST", "/images/create", [])
        items = [item async for item in images_api.pull("nginx")]
        assert items == []
