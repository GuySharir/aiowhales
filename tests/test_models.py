"""Tests for model parsing — container, image, volume, network, events."""

from datetime import datetime

import pytest

from aiowhales.models.container import Container, _parse_container
from aiowhales.models.events import DockerEvent, _parse_event
from aiowhales.models.exec_result import ExecResult
from aiowhales.models.image import BuildOutput, Image, PullProgress, PushProgress, _parse_image
from aiowhales.models.network import Network, _parse_network
from aiowhales.models.volume import Volume, _parse_volume
from aiowhales.testing import MockTransport
from aiowhales.api.containers import ContainersAPI

from .conftest import (
    CONTAINER_INSPECT_FIXTURE,
    CONTAINER_LIST_FIXTURE,
    CONTAINER_STOPPED_FIXTURE,
    IMAGE_INSPECT_FIXTURE,
    IMAGE_LIST_FIXTURE,
    NETWORK_INSPECT_FIXTURE,
    NETWORK_LIST_FIXTURE,
    VOLUME_INSPECT_FIXTURE,
    VOLUME_LIST_FIXTURE,
)


def _make_api():
    return ContainersAPI(MockTransport())


class TestContainerParsing:
    def test_parse_list_format(self):
        data = CONTAINER_LIST_FIXTURE[0]
        c = _parse_container(data, _make_api())
        assert c.id == "abc123def456"
        assert c.name == "web-app"
        assert c.image == "nginx:latest"
        assert c.status == "running"
        assert c.labels == {"app": "web", "env": "prod"}

    def test_parse_list_format_ports(self):
        data = CONTAINER_LIST_FIXTURE[0]
        c = _parse_container(data, _make_api())
        assert "80/tcp" in c.ports
        assert "443/tcp" in c.ports

    def test_parse_inspect_format(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        assert c.id == "abc123def456"
        assert c.name == "web-app"
        assert c.image == "nginx:latest"
        assert c.status == "running"

    def test_parse_inspect_env(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        assert c.env == {"FOO": "bar", "DEBUG": "1", "PATH": "/usr/bin"}

    def test_parse_inspect_labels(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        assert c.labels == {"app": "web", "env": "prod"}

    def test_parse_inspect_ports(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        assert "80/tcp" in c.ports
        assert "443/tcp" in c.ports

    def test_parse_inspect_created_datetime(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        assert isinstance(c.created, datetime)
        assert c.created.year == 2024

    def test_parse_list_created_timestamp(self):
        c = _parse_container(CONTAINER_LIST_FIXTURE[0], _make_api())
        assert isinstance(c.created, datetime)

    def test_parse_stopped_container(self):
        c = _parse_container(CONTAINER_STOPPED_FIXTURE, _make_api())
        assert c.status == "exited"
        assert c.name == "stopped-container"

    def test_parse_missing_fields_graceful(self):
        """Parsing minimal data should not raise."""
        c = _parse_container({"Id": "x"}, _make_api())
        assert c.id == "x"
        assert c.name == ""
        assert c.labels == {}
        assert c.env == {}

    def test_container_is_frozen(self):
        c = _parse_container(CONTAINER_INSPECT_FIXTURE, _make_api())
        with pytest.raises(AttributeError):
            c.status = "stopped"

    def test_parse_empty_names_list(self):
        data = {"Id": "x", "Names": [], "Created": 0}
        c = _parse_container(data, _make_api())
        assert c.name == ""

    def test_parse_name_strips_leading_slash(self):
        data = {"Id": "x", "Names": ["/my-container"], "Created": 0}
        c = _parse_container(data, _make_api())
        assert c.name == "my-container"

    def test_parse_invalid_created_string(self):
        data = {"Id": "x", "Name": "/test", "Created": "not-a-date",
                "State": {"Status": "running"}, "Config": {"Image": "x", "Labels": {}, "Env": []},
                "NetworkSettings": {"Ports": {}}}
        c = _parse_container(data, _make_api())
        assert c.created == datetime.min

    def test_parse_env_without_equals(self):
        """Env entries without '=' should be skipped."""
        data = {
            "Id": "x", "Name": "/test", "Created": "2024-01-01T00:00:00Z",
            "State": {"Status": "running"},
            "Config": {"Image": "x", "Labels": {}, "Env": ["NOEQUALS", "KEY=value"]},
            "NetworkSettings": {"Ports": {}},
        }
        c = _parse_container(data, _make_api())
        assert c.env == {"KEY": "value"}

    def test_parse_null_labels(self):
        data = {"Id": "x", "Names": ["/t"], "Image": "x", "State": "running",
                "Created": 0, "Labels": None, "Ports": []}
        c = _parse_container(data, _make_api())
        assert c.labels == {}


class TestImageParsing:
    def test_parse_list_format(self):
        img = _parse_image(IMAGE_LIST_FIXTURE[0])
        assert img.id == "sha256:abc123"
        assert img.tags == ["nginx:latest", "nginx:1.25"]
        assert img.size == 187000000

    def test_parse_inspect_format(self):
        img = _parse_image(IMAGE_INSPECT_FIXTURE)
        assert img.id == "sha256:abc123full"
        assert img.architecture == "amd64"
        assert img.os == "linux"

    def test_parse_labels_from_config(self):
        img = _parse_image(IMAGE_INSPECT_FIXTURE)
        assert img.labels.get("maintainer") == "NGINX"

    def test_parse_no_tags(self):
        img = _parse_image({"Id": "sha256:orphan", "Size": 0, "Created": 0})
        assert img.tags == []

    def test_image_is_frozen(self):
        img = _parse_image(IMAGE_LIST_FIXTURE[0])
        with pytest.raises(AttributeError):
            img.id = "new"

    def test_short_id(self):
        img = _parse_image({"Id": "sha256:abcdef1234567890", "Size": 0, "Created": 0})
        assert img.short_id == "sha256:abcde"

    def test_parse_created_timestamp(self):
        img = _parse_image(IMAGE_LIST_FIXTURE[0])
        assert isinstance(img.created, datetime)

    def test_parse_created_isoformat(self):
        img = _parse_image(IMAGE_INSPECT_FIXTURE)
        assert isinstance(img.created, datetime)
        assert img.created.year == 2024

    def test_parse_missing_fields(self):
        img = _parse_image({"Id": "x"})
        assert img.size == 0
        assert img.architecture == ""
        assert img.os == ""


class TestImageModels:
    def test_pull_progress_frozen(self):
        p = PullProgress(status="Downloading", layer_id="abc", progress="50%")
        with pytest.raises(AttributeError):
            p.status = "Done"

    def test_push_progress_frozen(self):
        p = PushProgress(status="Pushing", layer_id="abc", progress="50%")
        with pytest.raises(AttributeError):
            p.status = "Done"

    def test_build_output_frozen(self):
        b = BuildOutput(stream="Step 1/3", error="")
        with pytest.raises(AttributeError):
            b.stream = "Step 2/3"


class TestVolumeParsing:
    def test_parse_volume(self):
        v = _parse_volume(VOLUME_INSPECT_FIXTURE)
        assert v.name == "my-data"
        assert v.driver == "local"
        assert v.mountpoint == "/var/lib/docker/volumes/my-data/_data"
        assert v.labels == {"project": "myapp"}
        assert v.scope == "local"

    def test_parse_volume_created(self):
        v = _parse_volume(VOLUME_INSPECT_FIXTURE)
        assert isinstance(v.created, datetime)
        assert v.created.year == 2024

    def test_volume_is_frozen(self):
        v = _parse_volume(VOLUME_INSPECT_FIXTURE)
        with pytest.raises(AttributeError):
            v.name = "other"

    def test_parse_missing_fields(self):
        v = _parse_volume({"Name": "x"})
        assert v.driver == ""
        assert v.labels == {}

    def test_parse_null_labels(self):
        v = _parse_volume({"Name": "x", "Labels": None})
        assert v.labels == {}

    def test_parse_invalid_date(self):
        v = _parse_volume({"Name": "x", "CreatedAt": "not-a-date"})
        assert v.created == datetime.min


class TestNetworkParsing:
    def test_parse_network(self):
        n = _parse_network(NETWORK_INSPECT_FIXTURE)
        assert n.id == "net456"
        assert n.name == "my-network"
        assert n.driver == "bridge"
        assert n.scope == "local"
        assert n.labels == {"project": "myapp"}

    def test_parse_network_created(self):
        n = _parse_network(NETWORK_INSPECT_FIXTURE)
        assert isinstance(n.created, datetime)

    def test_network_is_frozen(self):
        n = _parse_network(NETWORK_INSPECT_FIXTURE)
        with pytest.raises(AttributeError):
            n.name = "other"

    def test_parse_missing_fields(self):
        n = _parse_network({"Id": "x"})
        assert n.name == ""
        assert n.driver == ""
        assert n.labels == {}

    def test_parse_null_labels(self):
        n = _parse_network({"Id": "x", "Labels": None})
        assert n.labels == {}


class TestEventParsing:
    def test_parse_event(self):
        from .conftest import EVENT_FIXTURE
        e = _parse_event(EVENT_FIXTURE)
        assert e.type == "container"
        assert e.action == "start"
        assert e.actor_id == "abc123"
        assert e.actor_attributes == {"name": "web-app", "image": "nginx:latest"}

    def test_parse_event_time(self):
        from .conftest import EVENT_FIXTURE
        e = _parse_event(EVENT_FIXTURE)
        assert isinstance(e.time, datetime)

    def test_event_is_frozen(self):
        from .conftest import EVENT_FIXTURE
        e = _parse_event(EVENT_FIXTURE)
        with pytest.raises(AttributeError):
            e.action = "stop"

    def test_event_raw_preserved(self):
        from .conftest import EVENT_FIXTURE
        e = _parse_event(EVENT_FIXTURE)
        assert e.raw == EVENT_FIXTURE

    def test_parse_missing_actor(self):
        e = _parse_event({"Type": "image", "Action": "pull", "time": 0})
        assert e.actor_id == ""
        assert e.actor_attributes == {}

    def test_parse_non_numeric_time(self):
        e = _parse_event({"Type": "x", "Action": "y", "time": "invalid"})
        assert e.time == datetime.min


class TestExecResult:
    def test_frozen(self):
        r = ExecResult(exit_code=0, output="hello")
        with pytest.raises(AttributeError):
            r.exit_code = 1

    def test_attributes(self):
        r = ExecResult(exit_code=42, output="some output")
        assert r.exit_code == 42
        assert r.output == "some output"

    def test_equality(self):
        a = ExecResult(exit_code=0, output="ok")
        b = ExecResult(exit_code=0, output="ok")
        assert a == b
