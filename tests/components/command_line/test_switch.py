"""The tests for the Command line switch platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import os
import tempfile
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import setup
from menuai.components.command_line import DOMAIN
from menuai.components.command_line.switch import CommandSwitch
from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN, SCAN_INTERVAL
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import mock_asyncio_subprocess_run

from tests.common import async_fire_time_changed


async def test_setup_platform_yaml(menuai: menuai) -> None:
    """Test setting up the platform with platform yaml."""
    await setup.async_setup_component(
        menuai,
        "switch",
        {
            "switch": {
                "platform": "command_line",
                "command": "echo 1",
                "payload_on": "1",
                "payload_off": "0",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0


async def test_state_integration_yaml(menuai: menuai) -> None:
    """Test with none state."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "switch_status")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_on": f"echo 1 > {path}",
                            "command_off": f"echo 0 > {path}",
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_ON

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF


async def test_state_value(menuai: menuai) -> None:
    """Test with state value."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "switch_status")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": f"cat {path}",
                            "command_on": f"echo 1 > {path}",
                            "command_off": f"echo 0 > {path}",
                            "value_template": '{{ value=="1" }}',
                            "icon": (
                                '{% if value=="1" %} mdi:on {% else %} mdi:off {% endif %}'
                            ),
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_ON
        assert entity_state.attributes.get("icon") == "mdi:on"

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF
        assert entity_state.attributes.get("icon") == "mdi:off"


async def test_state_json_value(menuai: menuai) -> None:
    """Test with state JSON value."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "switch_status")
        oncmd = json.dumps({"status": "ok"})
        offcmd = json.dumps({"status": "nope"})

        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": f"cat {path}",
                            "command_on": f"echo '{oncmd}' > {path}",
                            "command_off": f"echo '{offcmd}' > {path}",
                            "value_template": '{{ value_json.status=="ok" }}',
                            "icon": (
                                '{% if value_json.status=="ok" %} mdi:on'
                                "{% else %} mdi:off {% endif %}"
                            ),
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_ON
        assert entity_state.attributes.get("icon") == "mdi:on"

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF
        assert entity_state.attributes.get("icon") == "mdi:off"


async def test_state_code(menuai: menuai) -> None:
    """Test with state code."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "switch_status")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": f"cat {path}",
                            "command_on": f"echo 1 > {path}",
                            "command_off": f"echo 0 > {path}",
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_OFF

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_ON

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        assert entity_state
        assert entity_state.state == STATE_ON


async def test_assumed_state_should_be_true_if_command_state_is_none(
    menuai: menuai,
) -> None:
    """Test with state value."""

    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_on": "echo 'on command'",
                        "command_off": "echo 'off command'",
                        "name": "Test",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.attributes["assumed_state"]


async def test_assumed_state_should_absent_if_command_state_present(
    menuai: menuai,
) -> None:
    """Test with state value."""

    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_on": "echo 'on command'",
                        "command_off": "echo 'off command'",
                        "command_state": "cat {}",
                        "name": "Test",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert "assumed_state" not in entity_state.attributes


async def test_name_is_set_correctly(menuai: menuai) -> None:
    """Test that name is set correctly."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_on": "echo 'on command'",
                        "command_off": "echo 'off command'",
                        "name": "Test friendly name!",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("switch.test_friendly_name")
    assert entity_state
    assert entity_state.name == "Test friendly name!"


async def test_switch_command_state_fail(
    caplog: pytest.LogCaptureFixture, menuai: menuai
) -> None:
    """Test that switch failures are handled correctly."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_on": "exit 0",
                        "command_off": "exit 0'",
                        "command_state": "echo 1",
                        "name": "Test",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == "on"

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.test"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == "on"

    assert "Command failed" in caplog.text


async def test_switch_command_state_code_exceptions(
    caplog: pytest.LogCaptureFixture, menuai: menuai
) -> None:
    """Test that switch state code exceptions are handled correctly."""

    with mock_asyncio_subprocess_run(exception=asyncio.TimeoutError) as run:
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_on": "exit 0",
                            "command_off": "exit 0'",
                            "command_state": "echo 1",
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done()
        assert run.called
        assert "Timeout for command" in caplog.text

    with mock_asyncio_subprocess_run(returncode=127) as run:
        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL * 2)
        await menuai.async_block_till_done()
        assert run.called
        assert "Error trying to exec command" in caplog.text


async def test_switch_command_state_value_exceptions(
    caplog: pytest.LogCaptureFixture, menuai: menuai
) -> None:
    """Test that switch state value exceptions are handled correctly."""

    with mock_asyncio_subprocess_run(exception=asyncio.TimeoutError) as run:
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_on": "exit 0",
                            "command_off": "exit 0'",
                            "command_state": "echo 1",
                            "value_template": '{{ value=="1" }}',
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done()
        assert run.call_count == 1
        assert "Timeout for command" in caplog.text

    with mock_asyncio_subprocess_run(returncode=127) as run:
        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL * 2)
        await menuai.async_block_till_done()
        assert run.call_count == 1
        assert "Command failed (with return code 127)" in caplog.text


async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique_id option and if it only creates one switch per id."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_on": "echo on",
                        "command_off": "echo off",
                        "unique_id": "unique",
                        "name": "Test",
                    }
                },
                {
                    "switch": {
                        "command_on": "echo on",
                        "command_off": "echo off",
                        "unique_id": "not-so-unique-anymore",
                        "name": "Test2",
                    }
                },
                {
                    "switch": {
                        "command_on": "echo on",
                        "command_off": "echo off",
                        "unique_id": "not-so-unique-anymore",
                        "name": "Test3",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 2

    assert len(entity_registry.entities) == 2
    assert entity_registry.async_get_entity_id("switch", "command_line", "unique")
    assert entity_registry.async_get_entity_id(
        "switch", "command_line", "not-so-unique-anymore"
    )


async def test_command_failure(
    caplog: pytest.LogCaptureFixture, menuai: menuai
) -> None:
    """Test command failure."""

    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "switch": {
                        "command_off": "exit 33",
                        "name": "Test",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: "switch.test"}, blocking=True
    )
    assert "return code 33" in caplog.text


async def test_templating(menuai: menuai) -> None:
    """Test with templating."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "switch_status")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": f"cat {path}",
                            "command_on": f"echo 1 > {path}",
                            "command_off": f"echo 0 > {path}",
                            "value_template": '{{ value=="1" }}',
                            "icon": (
                                '{% if this.attributes.icon=="mdi:icon2" %} mdi:icon1 {% else %} mdi:icon2 {% endif %}'
                            ),
                            "name": "Test",
                        }
                    },
                    {
                        "switch": {
                            "command_state": f"cat {path}",
                            "command_on": f"echo 1 > {path}",
                            "command_off": f"echo 0 > {path}",
                            "value_template": '{{ value=="1" }}',
                            "icon": (
                                '{% if states("switch.test")=="off" %} mdi:off {% else %} mdi:on {% endif %}'
                            ),
                            "name": "Test2",
                        },
                    },
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("switch.test")
        entity_state2 = menuai.states.get("switch.test2")
        assert entity_state.state == STATE_OFF
        assert entity_state2.state == STATE_OFF

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test"},
            blocking=True,
        )
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.test2"},
            blocking=True,
        )

        entity_state = menuai.states.get("switch.test")
        entity_state2 = menuai.states.get("switch.test2")
        assert entity_state.state == STATE_ON
        assert entity_state.attributes.get("icon") == "mdi:icon2"
        assert entity_state2.state == STATE_ON
        assert entity_state2.attributes.get("icon") == "mdi:on"


async def test_updating_to_often(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling updating when command already running."""

    called = []
    wait_till_event = asyncio.Event()
    wait_till_event.set()

    class MockCommandSwitch(CommandSwitch):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update entity."""
            called.append(1)
            # Wait till event is set
            await wait_till_event.wait()

    with patch(
        "menuai.components.command_line.switch.CommandSwitch",
        side_effect=MockCommandSwitch,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": "echo 1",
                            "command_on": "echo 2",
                            "command_off": "echo 3",
                            "name": "Test",
                            "scan_interval": 10,
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

    assert not called
    assert (
        "Updating Command Line Switch Test took longer than the scheduled update interval"
        not in caplog.text
    )
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=11))
    await menuai.async_block_till_done()
    assert called
    called.clear()

    assert (
        "Updating Command Line Switch Test took longer than the scheduled update interval"
        not in caplog.text
    )

    # Simulate update takes too long
    wait_till_event.clear()
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    await asyncio.sleep(0)
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    wait_till_event.set()

    # Finish processing update
    await menuai.async_block_till_done()
    assert called
    assert (
        "Updating Command Line Switch Test took longer than the scheduled update interval"
        in caplog.text
    )


async def test_updating_manually(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling manual updating using menuai udate_entity service."""
    await setup.async_setup_component(menuai, HA_DOMAIN, {})
    called = []

    class MockCommandSwitch(CommandSwitch):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update slow."""
            called.append(1)

    with patch(
        "menuai.components.command_line.switch.CommandSwitch",
        side_effect=MockCommandSwitch,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "switch": {
                            "command_state": "echo 1",
                            "command_on": "echo 2",
                            "command_off": "echo 3",
                            "name": "Test",
                            "scan_interval": 10,
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert called
    called.clear()

    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["switch.test"]},
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
                    "switch": {
                        "command_state": "echo 1",
                        "command_on": "echo 2",
                        "command_off": "echo 3",
                        "name": "Test",
                        "value_template": "{{ value_json == 0 }}",
                        "availability": '{{ "sensor.input1" | has_value }}',
                        "icon": 'mdi:{{ states("sensor.input1") }}',
                    },
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

    menuai.states.async_set("sensor.input1", STATE_OFF)
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == STATE_OFF
    assert entity_state.attributes["icon"] == "mdi:off"

    menuai.states.async_set("sensor.input1", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE
    assert "icon" not in entity_state.attributes

    menuai.states.async_set("sensor.input1", STATE_ON)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"0\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == STATE_ON
    assert entity_state.attributes["icon"] == "mdi:on"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "switch": {
                        "command_state": "echo 1",
                        "command_on": "echo 2",
                        "command_off": "echo 3",
                        "name": "Test",
                        "value_template": "{{ x - 1 }}",
                        "availability": "{{ value == '50' }}",
                    },
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
    error = "Error parsing value for switch.test: 'x' is undefined"
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"51\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error not in caplog.text

    entity_state = menuai.states.get("switch.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE

    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error in caplog.text
