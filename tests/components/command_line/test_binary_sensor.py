"""The tests for the Command line Binary sensor platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import setup
from menuai.components.command_line.binary_sensor import CommandBinarySensor
from menuai.components.command_line.const import DOMAIN
from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import mock_asyncio_subprocess_run

from tests.common import async_fire_time_changed


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "name": "Test",
                        "command": "echo 1",
                        "payload_on": "1",
                        "payload_off": "0",
                        "command_timeout": 15,
                    }
                }
            ]
        }
    ],
)
async def test_setup_integration_yaml(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test sensor setup."""

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_ON
    assert entity_state.name == "Test"


async def test_setup_platform_yaml(menuai: menuai) -> None:
    """Test setting up the platform with platform yaml."""
    await setup.async_setup_component(
        menuai,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": "command_line",
                "command": "echo 1",
                "payload_on": "1",
                "payload_off": "0",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "name": "Test",
                        "command": "echo 10",
                        "payload_on": "1.0",
                        "payload_off": "0",
                        "value_template": "{{ value | multiply(0.1) }}",
                        "icon": (
                            '{% if this.attributes.icon=="mdi:icon2" %} mdi:icon1 {% else %} mdi:icon2 {% endif %}'
                        ),
                    }
                }
            ]
        }
    ],
)
async def test_template(menuai: menuai, load_yaml_integration: None) -> None:
    """Test setting the state with a template."""

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_ON
    assert entity_state.attributes.get("icon") == "mdi:icon2"

    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_ON
    assert entity_state.attributes.get("icon") == "mdi:icon1"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "name": "Test",
                        "command": "echo 0",
                        "payload_on": "1",
                        "payload_off": "0",
                    }
                }
            ]
        }
    ],
)
async def test_sensor_off(menuai: menuai, load_yaml_integration: None) -> None:
    """Test setting the state with a template."""

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_OFF


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "unique_id": "unique",
                        "command": "echo 0",
                    }
                },
                {
                    "binary_sensor": {
                        "unique_id": "not-so-unique-anymore",
                        "command": "echo 1",
                    }
                },
                {
                    "binary_sensor": {
                        "unique_id": "not-so-unique-anymore",
                        "command": "echo 2",
                    }
                },
            ]
        }
    ],
)
async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry, load_yaml_integration: None
) -> None:
    """Test unique_id option and if it only creates one binary sensor per id."""

    assert len(menuai.states.async_all()) == 2

    assert len(entity_registry.entities) == 2
    assert entity_registry.async_get_entity_id(
        "binary_sensor", "command_line", "unique"
    )
    assert entity_registry.async_get_entity_id(
        "binary_sensor", "command_line", "not-so-unique-anymore"
    )


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "command": "exit 33",
                    }
                }
            ]
        }
    ],
)
async def test_return_code(
    menuai: menuai, caplog: pytest.LogCaptureFixture, get_config: dict[str, Any]
) -> None:
    """Test setting the state with a template."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()
    assert "return code 33" in caplog.text


async def test_updating_to_often(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling updating when command already running."""

    wait_till_event = asyncio.Event()
    wait_till_event.set()
    called = []

    class MockCommandBinarySensor(CommandBinarySensor):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update the entity."""
            called.append(1)
            # Wait till event is set
            await wait_till_event.wait()

    with patch(
        "menuai.components.command_line.binary_sensor.CommandBinarySensor",
        side_effect=MockCommandBinarySensor,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "binary_sensor": {
                            "name": "Test",
                            "command": "echo 1",
                            "payload_on": "1",
                            "payload_off": "0",
                            "scan_interval": 10,
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

    assert called
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=15))
    wait_till_event.set()
    await asyncio.sleep(0)
    assert (
        "Updating Command Line Binary Sensor Test took longer than the scheduled update interval"
        not in caplog.text
    )

    # Simulate update takes too long
    wait_till_event.clear()
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    await asyncio.sleep(0)
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    wait_till_event.set()
    await asyncio.sleep(0)

    assert (
        "Updating Command Line Binary Sensor Test took longer than the scheduled update interval"
        in caplog.text
    )


async def test_updating_manually(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling manual updating using menuai udate_entity service."""
    await setup.async_setup_component(menuai, HA_DOMAIN, {})
    called = []

    class MockCommandBinarySensor(CommandBinarySensor):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update."""
            called.append(1)

    with patch(
        "menuai.components.command_line.binary_sensor.CommandBinarySensor",
        side_effect=MockCommandBinarySensor,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "binary_sensor": {
                            "name": "Test",
                            "command": "echo 1",
                            "payload_on": "1",
                            "payload_off": "0",
                            "scan_interval": 10,
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

    assert called
    called.clear()

    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["binary_sensor.test"]},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert called


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "name": "Test",
                        "command": "echo 10",
                        "payload_on": "1.0",
                        "payload_off": "0.0",
                        "value_template": "{{ value | multiply(0.1) }}",
                        "availability": '{{ "sensor.input1" | has_value }}',
                        "icon": 'mdi:{{ states("sensor.input1") }}',
                    }
                }
            ]
        }
    ],
)
async def test_availability(
    menuai: menuai,
    load_yaml_integration: None,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test availability."""
    menuai.states.async_set("sensor.input1", STATE_ON)
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_ON
    assert entity_state.attributes["icon"] == "mdi:on"

    menuai.states.async_set("sensor.input1", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"0"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE
    assert "icon" not in entity_state.attributes

    menuai.states.async_set("sensor.input1", STATE_OFF)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"0"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_OFF
    assert entity_state.attributes["icon"] == "mdi:off"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "binary_sensor": {
                        "name": "Test",
                        "command": "echo 10",
                        "payload_on": "1.0",
                        "payload_off": "0.0",
                        "value_template": "{{ x - 1 }}",
                        "availability": "{{ value == '50' }}",
                    }
                }
            ]
        }
    ],
)
async def test_availability_blocks_value_template(
    menuai: menuai,
    load_yaml_integration: None,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test availability blocks value_template from rendering."""
    error = "Error parsing value for binary_sensor.test: 'x' is undefined"
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"51\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error not in caplog.text

    entity_state = menuai.states.get("binary_sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE

    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error in caplog.text
