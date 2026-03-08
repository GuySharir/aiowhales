"""Tests for NetworksAPI."""

import pytest

from aiowhales.api.networks import NetworksAPI
from aiowhales.models.network import Network
from aiowhales.testing import MockTransport

from .conftest import NETWORK_INSPECT_FIXTURE, NETWORK_LIST_FIXTURE


@pytest.fixture
def api():
    transport = MockTransport()
    return NetworksAPI(transport), transport


class TestNetworksList:
    @pytest.mark.asyncio
    async def test_list_returns_networks(self, api):
        networks_api, transport = api
        transport.register("GET", "/networks", NETWORK_LIST_FIXTURE)
        result = await networks_api.list()
        assert len(result) == 2
        assert all(isinstance(n, Network) for n in result)

    @pytest.mark.asyncio
    async def test_list_names(self, api):
        networks_api, transport = api
        transport.register("GET", "/networks", NETWORK_LIST_FIXTURE)
        result = await networks_api.list()
        assert result[0].name == "bridge"
        assert result[1].name == "my-network"

    @pytest.mark.asyncio
    async def test_list_empty(self, api):
        networks_api, transport = api
        transport.register("GET", "/networks", [])
        result = await networks_api.list()
        assert result == []


class TestNetworksGet:
    @pytest.mark.asyncio
    async def test_get_by_id(self, api):
        networks_api, transport = api
        transport.register("GET", "/networks/net456", NETWORK_INSPECT_FIXTURE)
        n = await networks_api.get("net456")
        assert n.id == "net456"
        assert n.name == "my-network"
        assert n.driver == "bridge"


class TestNetworksCreate:
    @pytest.mark.asyncio
    async def test_create_basic(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/create", {"Id": "newnet123"})
        transport.register("GET", "/networks/newnet123", NETWORK_INSPECT_FIXTURE)
        n = await networks_api.create("my-network")
        assert isinstance(n, Network)

    @pytest.mark.asyncio
    async def test_create_with_driver(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/create", {"Id": "newnet"})
        transport.register("GET", "/networks/newnet", NETWORK_INSPECT_FIXTURE)
        await networks_api.create("overlay-net", driver="overlay")

    @pytest.mark.asyncio
    async def test_create_with_labels(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/create", {"Id": "newnet"})
        transport.register("GET", "/networks/newnet", NETWORK_INSPECT_FIXTURE)
        await networks_api.create("my-net", labels={"env": "prod"})


class TestNetworksRemove:
    @pytest.mark.asyncio
    async def test_remove(self, api):
        networks_api, transport = api
        await networks_api.remove("net456")
        assert transport.calls[0] == ("DELETE", "/networks/net456", {})


class TestNetworksConnect:
    @pytest.mark.asyncio
    async def test_connect(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/net456/connect", {})
        await networks_api.connect("net456", "container123")
        assert transport.calls[0][1] == "/networks/net456/connect"

    @pytest.mark.asyncio
    async def test_connect_with_aliases(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/net456/connect", {})
        await networks_api.connect("net456", "container123", alias1="web")


class TestNetworksDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/net456/disconnect", {})
        await networks_api.disconnect("net456", "container123")
        assert transport.calls[0][1] == "/networks/net456/disconnect"


class TestNetworksPrune:
    @pytest.mark.asyncio
    async def test_prune(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/prune", {
            "NetworksDeleted": [{"Name": "orphan1"}, {"Id": "orphan2"}]
        })
        result = await networks_api.prune()
        assert "orphan1" in result
        assert "orphan2" in result

    @pytest.mark.asyncio
    async def test_prune_empty(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/prune", {"NetworksDeleted": None})
        result = await networks_api.prune()
        assert result == []

    @pytest.mark.asyncio
    async def test_prune_no_key(self, api):
        networks_api, transport = api
        transport.register("POST", "/networks/prune", {})
        result = await networks_api.prune()
        assert result == []
