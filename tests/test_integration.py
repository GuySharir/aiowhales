"""Integration tests — require a running Docker daemon.

Run with:  pytest -m integration
"""

from __future__ import annotations

import contextlib
import uuid

import pytest

from aiowhales import AsyncDockerClient
from aiowhales.exceptions import ContainerNotFound, ImageNotFound, NetworkNotFound, VolumeNotFound
from aiowhales.models.container import Container, ContainerStats
from aiowhales.models.image import Image
from aiowhales.models.network import Network
from aiowhales.models.volume import Volume

pytestmark = pytest.mark.integration

# Use a unique prefix so parallel runs don't clash
_PREFIX = f"aiowhales-test-{uuid.uuid4().hex[:8]}"


def _name(suffix: str) -> str:
    return f"{_PREFIX}-{suffix}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def docker():
    async with AsyncDockerClient() as client:
        yield client


@pytest.fixture
async def container(docker):
    """Create a running container and clean up after the test."""
    c = await docker.containers.run(
        "alpine:latest",
        command=["sleep", "300"],
        name=_name("ctr"),
    )
    yield c
    with contextlib.suppress(ContainerNotFound):
        await docker.containers.remove(c.id, force=True)


@pytest.fixture
async def volume(docker):
    """Create a volume and clean up after the test."""
    v = await docker.volumes.create(_name("vol"), labels={"test": "aiowhales"})
    yield v
    with contextlib.suppress(VolumeNotFound):
        await docker.volumes.remove(v.name, force=True)


@pytest.fixture
async def network(docker):
    """Create a network and clean up after the test."""
    n = await docker.networks.create(_name("net"), labels={"test": "aiowhales"})
    yield n
    with contextlib.suppress(NetworkNotFound):
        await docker.networks.remove(n.id)


# ---------------------------------------------------------------------------
# Container integration tests
# ---------------------------------------------------------------------------


class TestContainerLifecycle:
    async def test_run_and_inspect(self, docker, container):
        assert isinstance(container, Container)
        assert container.status == "running"
        assert container.image == "alpine:latest"

    async def test_get_by_id(self, docker, container):
        fetched = await docker.containers.get(container.id)
        assert fetched.id == container.id
        assert fetched.name == _name("ctr")

    async def test_list_includes_container(self, docker, container):
        containers = await docker.containers.list()
        ids = [c.id for c in containers]
        assert container.id in ids

    async def test_list_all(self, docker):
        c = await docker.containers.run(
            "alpine:latest",
            command=["true"],
            name=_name("exited"),
            detach=False,
        )
        try:
            # Exited container should show up with all=True
            all_containers = await docker.containers.list(all=True)
            ids = [ct.id for ct in all_containers]
            assert c.id in ids
        finally:
            await docker.containers.remove(c.id, force=True)

    async def test_stop_and_restart(self, docker, container):
        await docker.containers.stop(container.id, timeout=3)
        stopped = await docker.containers.get(container.id)
        assert stopped.status == "exited"

        await docker.containers.restart(container.id)
        restarted = await docker.containers.get(container.id)
        assert restarted.status == "running"

    async def test_pause_unpause(self, docker, container):
        await docker.containers.pause(container.id)
        paused = await docker.containers.get(container.id)
        assert paused.status == "paused"

        await docker.containers.unpause(container.id)
        unpaused = await docker.containers.get(container.id)
        assert unpaused.status == "running"

    async def test_rename(self, docker, container):
        new_name = _name("renamed")
        await docker.containers.rename(container.id, new_name)
        renamed = await docker.containers.get(container.id)
        assert renamed.name == new_name

    async def test_wait_returns_exit_code(self, docker):
        c = await docker.containers.run(
            "alpine:latest",
            command=["sh", "-c", "exit 42"],
            name=_name("wait"),
            detach=True,
        )
        try:
            exit_code = await docker.containers.wait(c.id)
            assert exit_code == 42
        finally:
            await docker.containers.remove(c.id, force=True)

    async def test_remove_not_found_raises(self, docker):
        with pytest.raises(ContainerNotFound):
            await docker.containers.get("nonexistent_container_id_12345")


class TestContainerCreate:
    async def test_create_with_env(self, docker):
        c = await docker.containers.create(
            "alpine:latest",
            command=["sleep", "300"],
            name=_name("env"),
            env={"MY_VAR": "hello", "OTHER": "world"},
        )
        try:
            assert c.env.get("MY_VAR") == "hello"
            assert c.env.get("OTHER") == "world"
        finally:
            await docker.containers.remove(c.id, force=True)

    async def test_create_with_labels(self, docker):
        c = await docker.containers.create(
            "alpine:latest",
            command=["sleep", "300"],
            name=_name("labels"),
            labels={"app": "test", "version": "1.0"},
        )
        try:
            assert c.labels.get("app") == "test"
            assert c.labels.get("version") == "1.0"
        finally:
            await docker.containers.remove(c.id, force=True)


class TestContainerRunContextManager:
    async def test_remove_on_exit(self, docker):
        c = await docker.containers.run(
            "alpine:latest",
            command=["sleep", "300"],
            name=_name("ctx"),
            remove_on_exit=True,
        )
        cid = c.id
        async with c:
            assert c.status == "running"

        # Container should be removed after exiting context
        with pytest.raises(ContainerNotFound):
            await docker.containers.get(cid)


class TestContainerExec:
    async def test_exec_run(self, docker, container):
        result = await docker.containers.exec_run(container.id, ["echo", "hello"])
        assert result.exit_code == 0
        assert "hello" in result.output

    async def test_exec_nonzero_exit(self, docker, container):
        result = await docker.containers.exec_run(container.id, ["sh", "-c", "exit 2"])
        assert result.exit_code == 2


class TestContainerStats:
    async def test_stats_snapshot(self, docker, container):
        stats = await docker.containers.stats(container.id)
        assert isinstance(stats, ContainerStats)
        assert stats.memory_limit_mb > 0
        assert stats.pids >= 1


class TestContainerLogs:
    async def test_logs(self, docker):
        c = await docker.containers.run(
            "alpine:latest",
            command=["echo", "integration-test-output"],
            name=_name("logs"),
            detach=False,
        )
        try:
            lines = [line async for line in docker.containers.logs(c.id)]
            output = " ".join(line.text for line in lines)
            assert "integration-test-output" in output
        finally:
            await docker.containers.remove(c.id, force=True)


class TestContainerInstanceMethods:
    async def test_reload(self, docker, container):
        reloaded = await container.reload()
        assert reloaded.id == container.id

    async def test_instance_stop(self, docker, container):
        await container.stop(timeout=3)
        reloaded = await container.reload()
        assert reloaded.status == "exited"

    async def test_instance_exec(self, docker, container):
        result = await container.exec(["whoami"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Image integration tests
# ---------------------------------------------------------------------------


class TestImages:
    async def test_list(self, docker):
        images = await docker.images.list()
        assert len(images) > 0
        assert all(isinstance(img, Image) for img in images)

    async def test_get(self, docker):
        img = await docker.images.get("alpine:latest")
        assert isinstance(img, Image)
        assert "alpine:latest" in img.tags
        assert img.architecture != ""

    async def test_inspect_alias(self, docker):
        img = await docker.images.inspect("alpine:latest")
        assert isinstance(img, Image)

    async def test_tag_and_remove(self, docker):
        tag_name = f"aiowhales-test:{_PREFIX}"
        await docker.images.tag("alpine:latest", tag_name)

        # Verify the tag exists
        img = await docker.images.get(tag_name)
        assert tag_name in img.tags

        # Clean up
        await docker.images.remove(tag_name)
        with pytest.raises(ImageNotFound):
            await docker.images.get(tag_name)

    async def test_pull(self, docker):
        # Pull a tiny image
        progress_items = [p async for p in docker.images.pull("alpine:latest")]
        assert len(progress_items) > 0
        assert any(p.status for p in progress_items)

    async def test_not_found(self, docker):
        with pytest.raises(ImageNotFound):
            await docker.images.get("nonexistent_image_12345:latest")


# ---------------------------------------------------------------------------
# Volume integration tests
# ---------------------------------------------------------------------------


class TestVolumes:
    async def test_create_and_get(self, docker, volume):
        assert isinstance(volume, Volume)
        assert volume.driver == "local"

        fetched = await docker.volumes.get(volume.name)
        assert fetched.name == volume.name
        assert fetched.labels.get("test") == "aiowhales"

    async def test_list_includes_volume(self, docker, volume):
        volumes = await docker.volumes.list()
        names = [v.name for v in volumes]
        assert volume.name in names

    async def test_remove(self, docker):
        name = _name("vol-rm")
        await docker.volumes.create(name)
        await docker.volumes.remove(name)

        with pytest.raises(VolumeNotFound):
            await docker.volumes.get(name)

    async def test_not_found(self, docker):
        with pytest.raises(VolumeNotFound):
            await docker.volumes.get("nonexistent_volume_12345")


# ---------------------------------------------------------------------------
# Network integration tests
# ---------------------------------------------------------------------------


class TestNetworks:
    async def test_create_and_get(self, docker, network):
        assert isinstance(network, Network)
        assert network.driver == "bridge"

        fetched = await docker.networks.get(network.id)
        assert fetched.name == _name("net")
        assert fetched.labels.get("test") == "aiowhales"

    async def test_list_includes_network(self, docker, network):
        networks = await docker.networks.list()
        ids = [n.id for n in networks]
        assert network.id in ids

    async def test_connect_disconnect(self, docker, network, container):
        await docker.networks.connect(network.id, container.id)
        await docker.networks.disconnect(network.id, container.id)

    async def test_remove(self, docker):
        name = _name("net-rm")
        n = await docker.networks.create(name)
        await docker.networks.remove(n.id)

        with pytest.raises(NetworkNotFound):
            await docker.networks.get(n.id)

    async def test_not_found(self, docker):
        with pytest.raises(NetworkNotFound):
            await docker.networks.get("nonexistent_network_12345")


# ---------------------------------------------------------------------------
# Exec API integration tests
# ---------------------------------------------------------------------------


class TestExecAPI:
    async def test_create_start_inspect(self, docker, container):
        exec_id = await docker.exec.create(container.id, ["echo", "exec-test"])
        output = await docker.exec.start(exec_id)
        assert "exec-test" in output

        info = await docker.exec.inspect(exec_id)
        assert info["ExitCode"] == 0

    async def test_run_convenience(self, docker, container):
        result = await docker.exec.run(container.id, ["cat", "/etc/hostname"])
        assert result.exit_code == 0
        assert len(result.output) > 0

    async def test_create_with_env_and_workdir(self, docker, container):
        exec_id = await docker.exec.create(
            container.id,
            ["sh", "-c", "echo $MY_VAR && pwd"],
            env=["MY_VAR=integration"],
            workdir="/tmp",
        )
        output = await docker.exec.start(exec_id)
        assert "integration" in output
        assert "/tmp" in output


# ---------------------------------------------------------------------------
# Client-level integration tests
# ---------------------------------------------------------------------------


class TestClient:
    async def test_from_env(self):
        from aiowhales import from_env

        async with from_env() as docker:
            containers = await docker.containers.list()
            assert isinstance(containers, list)

    async def test_context_manager(self):
        async with AsyncDockerClient() as docker:
            images = await docker.images.list()
            assert isinstance(images, list)
