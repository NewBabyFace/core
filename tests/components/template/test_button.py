"""The tests for the Template button platform."""

import datetime as dt
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import setup
from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.template import DOMAIN
from menuai.components.template.button import DEFAULT_NAME
from menuai.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITY_ID,
    CONF_FRIENDLY_NAME,
    CONF_ICON,
    STATE_UNKNOWN,
)
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry, assert_setup_component

_TEST_BUTTON = "button.template_button"
_TEST_OPTIONS_BUTTON = "button.test"


@pytest.mark.parametrize(
    "config_entry_extra_options",
    [
        {},
        {
            "device_class": "update",
        },
    ],
)
async def test_setup_config_entry(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    config_entry_extra_options: dict[str, str],
) -> None:
    """Test the config flow."""

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "button",
            "press": [
                {
                    "service": "input_boolean.toggle",
                    "metadata": {},
                    "data": {},
                    "target": {"entity_id": "input_boolean.test"},
                }
            ],
        }
        | config_entry_extra_options,
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("button.my_template")
    assert state is not None
    assert state == snapshot


async def test_missing_optional_config(menuai: menuai) -> None:
    """Test: missing optional template is ok."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "button": {
                        "press": {"service": "script.press"},
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(menuai, STATE_UNKNOWN)


async def test_missing_emtpy_press_action_config(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test: missing optional template is ok."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "button": {
                        "press": [],
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(menuai, STATE_UNKNOWN)

    now = dt.datetime.now(dt.UTC)
    freezer.move_to(now)
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {CONF_ENTITY_ID: _TEST_BUTTON},
        blocking=True,
    )

    _verify(
        menuai,
        now.isoformat(),
    )


async def test_missing_required_keys(menuai: menuai) -> None:
    """Test: missing required fields will fail."""
    with assert_setup_component(0, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {"template": {"button": {}}},
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert menuai.states.async_all("button") == []


async def test_all_optional_config(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    calls: list[ServiceCall],
) -> None:
    """Test: including all optional templates is ok."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "unique_id": "test",
                    "button": {
                        "press": {
                            "service": "test.automation",
                            "data_template": {"caller": "{{ this.entity_id }}"},
                        },
                        "device_class": "restart",
                        "unique_id": "test",
                        "name": "test",
                        "icon": "mdi:test",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(
        menuai,
        STATE_UNKNOWN,
        {
            CONF_DEVICE_CLASS: "restart",
            CONF_FRIENDLY_NAME: "test",
            CONF_ICON: "mdi:test",
        },
        _TEST_OPTIONS_BUTTON,
    )

    now = dt.datetime.now(dt.UTC)
    freezer.move_to(now)
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {CONF_ENTITY_ID: _TEST_OPTIONS_BUTTON},
        blocking=True,
    )

    assert len(calls) == 1
    assert calls[0].data["caller"] == _TEST_OPTIONS_BUTTON

    _verify(
        menuai,
        now.isoformat(),
        {
            CONF_DEVICE_CLASS: "restart",
            CONF_FRIENDLY_NAME: "test",
            CONF_ICON: "mdi:test",
        },
        _TEST_OPTIONS_BUTTON,
    )

    assert entity_registry.async_get_entity_id("button", "template", "test-test")


async def test_name_template(menuai: menuai) -> None:
    """Test: name template."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "button": {
                        "press": {"service": "script.press"},
                        "name": "Button {{ 1 + 1 }}",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(
        menuai,
        STATE_UNKNOWN,
        {
            CONF_FRIENDLY_NAME: "Button 2",
        },
        "button.button_2",
    )


async def test_unique_id(menuai: menuai) -> None:
    """Test: unique id is ok."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "unique_id": "test",
                    "button": {
                        "press": {"service": "script.press"},
                        "unique_id": "test",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(menuai, STATE_UNKNOWN)


def _verify(
    menuai: menuai,
    expected_value: str,
    attributes: dict[str, Any] | None = None,
    entity_id: str = _TEST_BUTTON,
) -> None:
    """Verify button's state."""
    attributes = attributes or {}
    if CONF_FRIENDLY_NAME not in attributes:
        attributes[CONF_FRIENDLY_NAME] = DEFAULT_NAME
    state = menuai.states.get(entity_id)
    assert state.state == expected_value
    assert state.attributes == attributes


async def test_device_id(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for device for button template."""

    device_config_entry = MockConfigEntry()
    device_config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=device_config_entry.entry_id,
        identifiers={("test", "identifier_test")},
        connections={("mac", "30:31:32:33:34:35")},
    )
    await menuai.async_block_till_done()
    assert device_entry is not None
    assert device_entry.id is not None

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "button",
            "device_id": device_entry.id,
            "press": [
                {
                    "service": "input_boolean.toggle",
                    "metadata": {},
                    "data": {},
                    "target": {"entity_id": "input_boolean.test"},
                }
            ],
        },
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    template_entity = entity_registry.async_get("button.my_template")
    assert template_entity is not None
    assert template_entity.device_id == device_entry.id
