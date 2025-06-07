"""Test blueprints."""

from collections.abc import Iterator
import contextlib
from os import PathLike
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from menuai.components import template
from menuai.components.blueprint import (
    BLUEPRINT_SCHEMA,
    Blueprint,
    BlueprintInUse,
    DomainBlueprints,
)
from menuai.components.template import DOMAIN, SERVICE_RELOAD
from menuai.core import Context, menuai, callback
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util, yaml as yaml_util

from tests.common import async_mock_service

BUILTIN_BLUEPRINT_FOLDER = pathlib.Path(template.__file__).parent / "blueprints"


@contextlib.contextmanager
def patch_blueprint(
    blueprint_path: str, data_path: str | PathLike[str]
) -> Iterator[None]:
    """Patch blueprint loading from a different source."""
    orig_load = DomainBlueprints._load_blueprint

    @callback
    def mock_load_blueprint(self, path):
        if path != blueprint_path:
            pytest.fail(f"Unexpected blueprint {path}")
            return orig_load(self, path)

        return Blueprint(
            yaml_util.load_yaml(data_path),
            expected_domain=self.domain,
            path=path,
            schema=BLUEPRINT_SCHEMA,
        )

    with patch(
        "menuai.components.blueprint.models.DomainBlueprints._load_blueprint",
        mock_load_blueprint,
    ):
        yield


@contextlib.contextmanager
def patch_invalid_blueprint() -> Iterator[None]:
    """Patch blueprint returning an invalid one."""

    @callback
    def mock_load_blueprint(self, path):
        return Blueprint(
            {
                "blueprint": {
                    "domain": "template",
                    "name": "Invalid template blueprint",
                },
                "binary_sensor": {},
                "sensor": {},
            },
            expected_domain=self.domain,
            path=path,
            schema=BLUEPRINT_SCHEMA,
        )

    with patch(
        "menuai.components.blueprint.models.DomainBlueprints._load_blueprint",
        mock_load_blueprint,
    ):
        yield


async def test_inverted_binary_sensor(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test inverted binary sensor blueprint."""
    menuai.states.async_set("binary_sensor.foo", "on", {"friendly_name": "Foo"})
    menuai.states.async_set("binary_sensor.bar", "off", {"friendly_name": "Bar"})

    with patch_blueprint(
        "inverted_binary_sensor.yaml",
        BUILTIN_BLUEPRINT_FOLDER / "inverted_binary_sensor.yaml",
    ):
        assert await async_setup_component(
            menuai,
            "template",
            {
                "template": [
                    {
                        "use_blueprint": {
                            "path": "inverted_binary_sensor.yaml",
                            "input": {"reference_entity": "binary_sensor.foo"},
                        },
                        "name": "Inverted foo",
                    },
                    {
                        "use_blueprint": {
                            "path": "inverted_binary_sensor.yaml",
                            "input": {"reference_entity": "binary_sensor.bar"},
                        },
                        "name": "Inverted bar",
                    },
                ]
            },
        )

    menuai.states.async_set("binary_sensor.foo", "off", {"friendly_name": "Foo"})
    menuai.states.async_set("binary_sensor.bar", "on", {"friendly_name": "Bar"})
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.foo").state == "off"
    assert menuai.states.get("binary_sensor.bar").state == "on"

    inverted_foo = menuai.states.get("binary_sensor.inverted_foo")
    assert inverted_foo
    assert inverted_foo.state == "on"

    inverted_bar = menuai.states.get("binary_sensor.inverted_bar")
    assert inverted_bar
    assert inverted_bar.state == "off"

    foo_template = template.helpers.blueprint_in_template(menuai, "binary_sensor.foo")
    inverted_foo_template = template.helpers.blueprint_in_template(
        menuai, "binary_sensor.inverted_foo"
    )
    assert foo_template is None
    assert inverted_foo_template == "inverted_binary_sensor.yaml"

    inverted_binary_sensor_blueprint_entity_ids = (
        template.helpers.templates_with_blueprint(menuai, "inverted_binary_sensor.yaml")
    )
    assert len(inverted_binary_sensor_blueprint_entity_ids) == 2

    assert len(template.helpers.templates_with_blueprint(menuai, "dummy.yaml")) == 0

    with pytest.raises(BlueprintInUse):
        await template.async_get_blueprints(menuai).async_remove_blueprint(
            "inverted_binary_sensor.yaml"
        )


async def test_reload_template_when_blueprint_changes(menuai: menuai) -> None:
    """Test a template is updated at reload if the blueprint has changed."""
    menuai.states.async_set("binary_sensor.foo", "on", {"friendly_name": "Foo"})
    config = {
        DOMAIN: [
            {
                "use_blueprint": {
                    "path": "inverted_binary_sensor.yaml",
                    "input": {"reference_entity": "binary_sensor.foo"},
                },
                "name": "Inverted foo",
            },
        ]
    }
    with patch_blueprint(
        "inverted_binary_sensor.yaml",
        BUILTIN_BLUEPRINT_FOLDER / "inverted_binary_sensor.yaml",
    ):
        assert await async_setup_component(menuai, DOMAIN, config)

    menuai.states.async_set("binary_sensor.foo", "off", {"friendly_name": "Foo"})
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.foo").state == "off"

    inverted = menuai.states.get("binary_sensor.inverted_foo")
    assert inverted
    assert inverted.state == "on"

    # Reload the automations without any change, but with updated blueprint
    blueprint_config = yaml_util.load_yaml(
        BUILTIN_BLUEPRINT_FOLDER / "inverted_binary_sensor.yaml"
    )
    blueprint_config["binary_sensor"]["state"] = "{{ states(reference_entity) }}"
    with (
        patch(
            "menuai.config.load_yaml_config_file",
            autospec=True,
            return_value=config,
        ),
        patch(
            "menuai.components.blueprint.models.yaml_util.load_yaml_dict",
            autospec=True,
            return_value=blueprint_config,
        ),
    ):
        await menuai.services.async_call(DOMAIN, SERVICE_RELOAD, blocking=True)

    menuai.states.async_set("binary_sensor.foo", "off", {"friendly_name": "Foo"})
    await menuai.async_block_till_done()

    not_inverted = menuai.states.get("binary_sensor.inverted_foo")
    assert not_inverted
    assert not_inverted.state == "off"

    menuai.states.async_set("binary_sensor.foo", "on", {"friendly_name": "Foo"})
    await menuai.async_block_till_done()

    not_inverted = menuai.states.get("binary_sensor.inverted_foo")
    assert not_inverted
    assert not_inverted.state == "on"


@pytest.mark.parametrize(
    ("blueprint"),
    ["test_event_sensor.yaml", "test_event_sensor_legacy_schema.yaml"],
)
async def test_trigger_event_sensor(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    blueprint: str,
) -> None:
    """Test event sensor blueprint."""
    assert await async_setup_component(
        menuai,
        "template",
        {
            "template": [
                {
                    "use_blueprint": {
                        "path": blueprint,
                        "input": {
                            "event_type": "my_custom_event",
                            "event_data": {"foo": "bar"},
                        },
                    },
                    "name": "My Custom Event",
                },
            ]
        },
    )

    context = Context()
    now = dt_util.utcnow()
    with patch("menuai.util.dt.now", return_value=now):
        menuai.bus.async_fire(
            "my_custom_event", {"foo": "bar", "beer": 2}, context=context
        )
        await menuai.async_block_till_done()

    date_state = menuai.states.get("sensor.my_custom_event")
    assert date_state is not None
    assert date_state.state == now.isoformat(timespec="seconds")
    data = date_state.attributes.get("data")
    assert data is not None
    assert data != ""
    assert data.get("foo") == "bar"
    assert data.get("beer") == 2

    inverted_foo_template = template.helpers.blueprint_in_template(
        menuai, "sensor.my_custom_event"
    )
    assert inverted_foo_template == blueprint

    inverted_binary_sensor_blueprint_entity_ids = (
        template.helpers.templates_with_blueprint(menuai, blueprint)
    )
    assert len(inverted_binary_sensor_blueprint_entity_ids) == 1

    with pytest.raises(BlueprintInUse):
        await template.async_get_blueprints(menuai).async_remove_blueprint(blueprint)


@pytest.mark.parametrize(
    ("blueprint", "override"),
    [
        # Override a blueprint with modern schema with legacy schema
        (
            "test_event_sensor.yaml",
            {"trigger": {"platform": "event", "event_type": "override"}},
        ),
        # Override a blueprint with modern schema with modern schema
        (
            "test_event_sensor.yaml",
            {"triggers": {"platform": "event", "event_type": "override"}},
        ),
        # Override a blueprint with legacy schema with legacy schema
        (
            "test_event_sensor_legacy_schema.yaml",
            {"trigger": {"platform": "event", "event_type": "override"}},
        ),
        # Override a blueprint with legacy schema with modern schema
        (
            "test_event_sensor_legacy_schema.yaml",
            {"triggers": {"platform": "event", "event_type": "override"}},
        ),
    ],
)
async def test_blueprint_template_override(
    menuai: menuai, blueprint: str, override: dict
) -> None:
    """Test blueprint template where the template config overrides the blueprint."""
    assert await async_setup_component(
        menuai,
        "template",
        {
            "template": [
                {
                    "use_blueprint": {
                        "path": blueprint,
                        "input": {
                            "event_type": "my_custom_event",
                            "event_data": {"foo": "bar"},
                        },
                    },
                    "name": "My Custom Event",
                }
                | override,
            ]
        },
    )
    await menuai.async_block_till_done()

    date_state = menuai.states.get("sensor.my_custom_event")
    assert date_state is not None
    assert date_state.state == "unknown"

    context = Context()
    now = dt_util.utcnow()
    with patch("menuai.util.dt.now", return_value=now):
        menuai.bus.async_fire(
            "my_custom_event", {"foo": "bar", "beer": 2}, context=context
        )
        await menuai.async_block_till_done()

    date_state = menuai.states.get("sensor.my_custom_event")
    assert date_state is not None
    assert date_state.state == "unknown"

    context = Context()
    now = dt_util.utcnow()
    with patch("menuai.util.dt.now", return_value=now):
        menuai.bus.async_fire("override", {"foo": "bar", "beer": 2}, context=context)
        await menuai.async_block_till_done()

    date_state = menuai.states.get("sensor.my_custom_event")
    assert date_state is not None
    assert date_state.state == now.isoformat(timespec="seconds")
    data = date_state.attributes.get("data")
    assert data is not None
    assert data != ""
    assert data.get("foo") == "bar"
    assert data.get("beer") == 2

    inverted_foo_template = template.helpers.blueprint_in_template(
        menuai, "sensor.my_custom_event"
    )
    assert inverted_foo_template == blueprint

    inverted_binary_sensor_blueprint_entity_ids = (
        template.helpers.templates_with_blueprint(menuai, blueprint)
    )
    assert len(inverted_binary_sensor_blueprint_entity_ids) == 1

    with pytest.raises(BlueprintInUse):
        await template.async_get_blueprints(menuai).async_remove_blueprint(blueprint)


async def test_domain_blueprint(menuai: menuai) -> None:
    """Test DomainBlueprint services."""
    reload_handler_calls = async_mock_service(menuai, DOMAIN, SERVICE_RELOAD)
    mock_create_file = MagicMock()
    mock_create_file.return_value = True

    with patch(
        "menuai.components.blueprint.models.DomainBlueprints._create_file",
        mock_create_file,
    ):
        await template.async_get_blueprints(menuai).async_add_blueprint(
            Blueprint(
                {
                    "blueprint": {
                        "domain": DOMAIN,
                        "name": "Test",
                    },
                },
                expected_domain="template",
                path="xxx",
                schema=BLUEPRINT_SCHEMA,
            ),
            "xxx",
            True,
        )
    assert len(reload_handler_calls) == 1


async def test_invalid_blueprint(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test an invalid blueprint definition."""

    with patch_invalid_blueprint():
        assert await async_setup_component(
            menuai,
            "template",
            {
                "template": [
                    {
                        "use_blueprint": {
                            "path": "invalid.yaml",
                        },
                        "name": "Invalid blueprint instance",
                    },
                ]
            },
        )

    assert "more than one platform defined per blueprint" in caplog.text
    blueprints = await template.async_get_blueprints(menuai).async_get_blueprints()
    assert "invalid.yaml" not in blueprints


async def test_no_blueprint(menuai: menuai) -> None:
    """Test templates without blueprints."""
    with patch_blueprint(
        "inverted_binary_sensor.yaml",
        BUILTIN_BLUEPRINT_FOLDER / "inverted_binary_sensor.yaml",
    ):
        assert await async_setup_component(
            menuai,
            "template",
            {
                "template": [
                    {"binary_sensor": {"name": "test entity", "state": "off"}},
                    {
                        "use_blueprint": {
                            "path": "inverted_binary_sensor.yaml",
                            "input": {"reference_entity": "binary_sensor.foo"},
                        },
                        "name": "inverted entity",
                    },
                ]
            },
        )

    menuai.states.async_set("binary_sensor.foo", "off", {"friendly_name": "Foo"})
    await menuai.async_block_till_done()

    assert (
        len(
            template.helpers.templates_with_blueprint(
                menuai, "inverted_binary_sensor.yaml"
            )
        )
        == 1
    )
    assert (
        template.helpers.blueprint_in_template(menuai, "binary_sensor.test_entity")
        is None
    )
