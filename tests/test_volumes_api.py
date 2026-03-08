"""Tests for VolumesAPI."""

import pytest

from aiowhales.api.volumes import VolumesAPI
from aiowhales.models.volume import Volume
from aiowhales.testing import MockTransport

from .conftest import VOLUME_INSPECT_FIXTURE, VOLUME_LIST_FIXTURE


@pytest.fixture
def api():
    transport = MockTransport()
    return VolumesAPI(transport), transport


class TestVolumesList:
    @pytest.mark.asyncio
    async def test_list_returns_volumes(self, api):
        volumes_api, transport = api
        transport.register("GET", "/volumes", VOLUME_LIST_FIXTURE)
        result = await volumes_api.list()
        assert len(result) == 2
        assert all(isinstance(v, Volume) for v in result)

    @pytest.mark.asyncio
    async def test_list_names(self, api):
        volumes_api, transport = api
        transport.register("GET", "/volumes", VOLUME_LIST_FIXTURE)
        result = await volumes_api.list()
        assert result[0].name == "my-data"
        assert result[1].name == "db-data"

    @pytest.mark.asyncio
    async def test_list_empty(self, api):
        volumes_api, transport = api
        transport.register("GET", "/volumes", {"Volumes": []})
        result = await volumes_api.list()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_null_volumes(self, api):
        volumes_api, transport = api
        transport.register("GET", "/volumes", {"Volumes": None})
        result = await volumes_api.list()
        assert result == []


class TestVolumesGet:
    @pytest.mark.asyncio
    async def test_get_by_name(self, api):
        volumes_api, transport = api
        transport.register("GET", "/volumes/my-data", VOLUME_INSPECT_FIXTURE)
        v = await volumes_api.get("my-data")
        assert v.name == "my-data"
        assert v.driver == "local"
        assert v.labels == {"project": "myapp"}


class TestVolumesCreate:
    @pytest.mark.asyncio
    async def test_create_basic(self, api):
        volumes_api, transport = api
        transport.register("POST", "/volumes/create", VOLUME_INSPECT_FIXTURE)
        v = await volumes_api.create("my-data")
        assert isinstance(v, Volume)
        assert v.name == "my-data"

    @pytest.mark.asyncio
    async def test_create_with_labels(self, api):
        volumes_api, transport = api
        transport.register("POST", "/volumes/create", VOLUME_INSPECT_FIXTURE)
        await volumes_api.create("my-data", labels={"env": "test"})

    @pytest.mark.asyncio
    async def test_create_with_driver(self, api):
        volumes_api, transport = api
        transport.register("POST", "/volumes/create", VOLUME_INSPECT_FIXTURE)
        await volumes_api.create("my-data", driver="nfs")


class TestVolumesRemove:
    @pytest.mark.asyncio
    async def test_remove(self, api):
        volumes_api, transport = api
        await volumes_api.remove("my-data")
        assert transport.calls[0] == ("DELETE", "/volumes/my-data", {})

    @pytest.mark.asyncio
    async def test_remove_force(self, api):
        volumes_api, transport = api
        await volumes_api.remove("my-data", force=True)
        assert transport.calls[0][2].get("force") == "true"


class TestVolumesPrune:
    @pytest.mark.asyncio
    async def test_prune(self, api):
        volumes_api, transport = api
        transport.register("POST", "/volumes/prune", {"VolumesDeleted": ["vol1", "vol2"]})
        result = await volumes_api.prune()
        assert result == ["vol1", "vol2"]

    @pytest.mark.asyncio
    async def test_prune_empty(self, api):
        volumes_api, transport = api
        transport.register("POST", "/volumes/prune", {"VolumesDeleted": None})
        result = await volumes_api.prune()
        assert result == []
