"""The tests the cover command line platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import os
import tempfile
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import setup
from menuai.components.command_line import DOMAIN
from menuai.components.command_line.cover import CommandCover
from menuai.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SCAN_INTERVAL,
    CoverState,
)
from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
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
        "cover",
        {
            "cover": {
                "platform": "command_line",
                "command": "echo 1",
                "payload_on": "1",
                "payload_off": "0",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0


async def test_no_poll_when_cover_has_no_command_state(menuai: menuai) -> None:
    """Test that the cover does not polls when there's no state command."""

    with mock_asyncio_subprocess_run(b"50\n") as mock_subprocess_run:
        assert await setup.async_setup_component(
            menuai,
            COVER_DOMAIN,
            {
                COVER_DOMAIN: [
                    {"platform": "command_line", "covers": {"test": {}}},
                ]
            },
        )
        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done()
        assert not mock_subprocess_run.called


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "cover": {
                        "command_state": "echo state",
                        "name": "Test",
                    },
                }
            ]
        }
    ],
)
async def test_poll_when_cover_has_command_state(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test that the cover polls when there's a state  command."""

    with mock_asyncio_subprocess_run(b"50\n") as mock_subprocess_run:
        async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done()
        mock_subprocess_run.assert_called_once_with(
            "echo state",
            close_fds=False,
            stdout=-1,
        )


async def test_state_value(menuai: menuai) -> None:
    """Test with state value."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "cover_status")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "cover": {
                            "command_state": f"cat {path}",
                            "command_open": f"echo 1 > {path}",
                            "command_close": f"echo 1 > {path}",
                            "command_stop": f"echo 0 > {path}",
                            "value_template": "{{ value }}",
                            "name": "Test",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.state == "unknown"

        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )
        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.state == "open"

        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )
        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.state == "open"

        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )
        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.state == "closed"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "cover": {
                        "command_open": "exit 1",
                        "name": "Test",
                    }
                }
            ]
        }
    ],
)
async def test_move_cover_failure(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test command failure."""

    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )
    assert "Command failed" in caplog.text
    assert "return code 1" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "cover": {
                        "command_open": "echo open",
                        "command_close": "echo close",
                        "command_stop": "echo stop",
                        "unique_id": "unique",
                        "name": "Test",
                    }
                },
                {
                    "cover": {
                        "command_open": "echo open",
                        "command_close": "echo close",
                        "command_stop": "echo stop",
                        "unique_id": "not-so-unique-anymore",
                        "name": "Test2",
                    }
                },
                {
                    "cover": {
                        "command_open": "echo open",
                        "command_close": "echo close",
                        "command_stop": "echo stop",
                        "unique_id": "not-so-unique-anymore",
                        "name": "Test3",
                    }
                },
            ]
        }
    ],
)
async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry, load_yaml_integration: None
) -> None:
    """Test unique_id option and if it only creates one cover per id."""
    assert len(menuai.states.async_all()) == 2

    assert len(entity_registry.entities) == 2
    assert entity_registry.async_get_entity_id("cover", "command_line", "unique")
    assert entity_registry.async_get_entity_id(
        "cover", "command_line", "not-so-unique-anymore"
    )


async def test_updating_to_often(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling updating when command already running."""

    called = []
    wait_till_event = asyncio.Event()
    wait_till_event.set()

    class MockCommandCover(CommandCover):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update the entity."""
            called.append(1)
            # Add waiting time
            await wait_till_event.wait()

    with patch(
        "menuai.components.command_line.cover.CommandCover",
        side_effect=MockCommandCover,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "cover": {
                            "command_state": "echo 1",
                            "value_template": "{{ value }}",
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
        "Updating Command Line Cover Test took longer than the scheduled update interval"
        not in caplog.text
    )
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=11))
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert called
    called.clear()

    assert (
        "Updating Command Line Cover Test took longer than the scheduled update interval"
        not in caplog.text
    )

    # Simulate update takes too long
    wait_till_event.clear()
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    await asyncio.sleep(0)
    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    wait_till_event.set()

    # Finish processing update
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert called
    assert (
        "Updating Command Line Cover Test took longer than the scheduled update interval"
        in caplog.text
    )


async def test_updating_manually(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling manual updating using menuai udate_entity service."""
    await setup.async_setup_component(menuai, HA_DOMAIN, {})
    called = []

    class MockCommandCover(CommandCover):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update."""
            called.append(1)

    with patch(
        "menuai.components.command_line.cover.CommandCover",
        side_effect=MockCommandCover,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "cover": {
                            "command_state": "echo 1",
                            "value_template": "{{ value }}",
                            "name": "Test",
                            "scan_interval": 10,
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=10))
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert called
    called.clear()

    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["cover.test"]},
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
                    "cover": {
                        "command_state": "echo 10",
                        "name": "Test",
                        "value_template": "{{ value }}",
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

    menuai.states.async_set("sensor.input1", "on")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("cover.test")
    assert entity_state
    assert entity_state.state == CoverState.OPEN
    assert entity_state.attributes["icon"] == "mdi:on"

    menuai.states.async_set("sensor.input1", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("cover.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE
    assert "icon" not in entity_state.attributes

    menuai.states.async_set("sensor.input1", "off")
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"25\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("cover.test")
    assert entity_state
    assert entity_state.state == CoverState.OPEN
    assert entity_state.attributes["icon"] == "mdi:off"


async def test_icon_template(menuai: menuai) -> None:
    """Test with state value."""
    with tempfile.TemporaryDirectory() as tempdirname:
        path = os.path.join(tempdirname, "cover_status_icon")
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "cover": {
                            "command_state": f"cat {path}",
                            "command_open": f"echo 100 > {path}",
                            "command_close": f"echo 0 > {path}",
                            "command_stop": f"echo 0 > {path}",
                            "name": "Test",
                            "icon": '{% if this.attributes.icon=="mdi:icon2" %} mdi:icon1 {% else %} mdi:icon2 {% endif %}',
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )

        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )
        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.attributes.get("icon") == "mdi:icon1"

        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: "cover.test"},
            blocking=True,
        )
        entity_state = menuai.states.get("cover.test")
        assert entity_state
        assert entity_state.attributes.get("icon") == "mdi:icon2"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "cover": {
                        "command_state": "echo 10",
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
    error = "Error parsing value for cover.test: 'x' is undefined"
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"51\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error not in caplog.text

    entity_state = menuai.states.get("cover.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE

    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error in caplog.text
