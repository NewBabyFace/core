"""The tests for the Command line sensor platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import setup
from menuai.components.command_line import DOMAIN
from menuai.components.command_line.sensor import CommandSensor
from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import mock_asyncio_subprocess_run

from tests.common import async_fire_time_changed


async def test_setup_platform_yaml(menuai: menuai) -> None:
    """Test setting up the platform with platform yaml."""
    await setup.async_setup_component(
        menuai,
        "sensor",
        {
            "sensor": {
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
                    "sensor": {
                        "name": "Test",
                        "command": "echo 5",
                        "unit_of_measurement": "in",
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

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "5"
    assert entity_state.name == "Test"
    assert entity_state.attributes["unit_of_measurement"] == "in"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo 50",
                        "unit_of_measurement": "in",
                        "value_template": "{{ value | multiply(0.1) }}",
                        "icon": "mdi:console",
                    }
                }
            ]
        }
    ],
)
async def test_template(menuai: menuai, load_yaml_integration: None) -> None:
    """Test command sensor with template."""

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert float(entity_state.state) == 5
    assert entity_state.attributes.get("icon") == "mdi:console"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo {{ states.sensor.input_sensor.state }}",
                    }
                }
            ]
        }
    ],
)
async def test_template_render(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Ensure command with templates get rendered properly."""
    menuai.states.async_set("sensor.input_sensor", "sensor_value")

    # Give time for template to load
    async_fire_time_changed(
        menuai,
        dt_util.utcnow() + timedelta(minutes=1),
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "sensor_value"


async def test_template_render_with_quote(menuai: menuai) -> None:
    """Ensure command with templates and quotes get rendered properly."""
    menuai.states.async_set("sensor.input_sensor", "sensor_value")
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": 'echo "{{ states.sensor.input_sensor.state }}" "3 4"',
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    with mock_asyncio_subprocess_run(b"Works\n") as mock_subprocess_run:
        # Give time for template to load
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(minutes=1),
        )
        await menuai.async_block_till_done(wait_background_tasks=True)

        assert len(mock_subprocess_run.mock_calls) == 1
        mock_subprocess_run.assert_called_with(
            'echo "sensor_value" "3 4"',
            stdout=-1,
            close_fds=False,
        )


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo {{ this template doesn't parse",
                    }
                }
            ]
        }
    ],
)
async def test_bad_template_render(
    caplog: pytest.LogCaptureFixture, menuai: menuai, get_config: dict[str, Any]
) -> None:
    """Test rendering a broken template."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    assert "Error rendering command template" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "asdfasdf",
                    }
                }
            ]
        }
    ],
)
async def test_bad_command(menuai: menuai, get_config: dict[str, Any]) -> None:
    """Test bad command."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "unknown"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "exit 33",
                    }
                }
            ]
        }
    ],
)
async def test_return_code(
    caplog: pytest.LogCaptureFixture, menuai: menuai, get_config: dict[str, Any]
) -> None:
    """Test that an error return code is logged."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    assert "return code 33" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": (
                            'echo { \\"key\\": \\"some_json_value\\", \\"another_key\\": '
                            '\\"another_json_value\\", \\"key_three\\": \\"value_three\\" }'
                        ),
                        "json_attributes": ["key", "another_key", "key_three"],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test attributes get extracted from a JSON result."""
    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "unknown"
    assert entity_state.attributes["key"] == "some_json_value"
    assert entity_state.attributes["another_key"] == "another_json_value"
    assert entity_state.attributes["key_three"] == "value_three"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": (
                            'echo { \\"key\\": \\"some_json_value\\", \\"another_key\\": '
                            '\\"another_json_value\\", \\"key_three\\": \\"value_three\\" }'
                        ),
                        "json_attributes": ["key", "another_key", "key_three"],
                        "value_template": '{{ value_json["key"] }}',
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs_and_value_template(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test json_attributes can be used together with value_template."""
    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "some_json_value"
    assert entity_state.attributes["key"] == "some_json_value"
    assert entity_state.attributes["another_key"] == "another_json_value"
    assert entity_state.attributes["key_three"] == "value_three"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo",
                        "json_attributes": ["key"],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs_no_data(
    caplog: pytest.LogCaptureFixture, menuai: menuai, get_config: dict[str, Any]
) -> None:
    """Test attributes when no JSON result fetched."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert "key" not in entity_state.attributes
    assert "Empty reply found when expecting JSON data" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo [1, 2, 3]",
                        "json_attributes": ["key"],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs_not_dict(
    caplog: pytest.LogCaptureFixture, menuai: menuai, get_config: dict[str, Any]
) -> None:
    """Test attributes when the return value not a dict."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert "key" not in entity_state.attributes
    assert "JSON result was not a dictionary" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo This is text rather than JSON data.",
                        "json_attributes": ["key"],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs_bad_json(
    caplog: pytest.LogCaptureFixture, menuai: menuai, get_config: dict[str, Any]
) -> None:
    """Test attributes when the return value is invalid JSON."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert "key" not in entity_state.attributes
    assert "Unable to parse output as JSON" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": (
                            'echo { \\"key\\": \\"some_json_value\\", \\"another_key\\": '
                            '\\"another_json_value\\", \\"key_three\\": \\"value_three\\" }'
                        ),
                        "json_attributes": [
                            "key",
                            "another_key",
                            "key_three",
                            "missing_key",
                        ],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_missing_json_attrs(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test attributes when an expected key is missing."""

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.attributes["key"] == "some_json_value"
    assert entity_state.attributes["another_key"] == "another_json_value"
    assert entity_state.attributes["key_three"] == "value_three"
    assert "missing_key" not in entity_state.attributes


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": (
                            'echo { \\"key\\": \\"some_json_value\\", \\"another_key\\": '
                            '\\"another_json_value\\", \\"key_three\\": \\"value_three\\" }'
                        ),
                        "json_attributes": ["key", "another_key"],
                    }
                }
            ]
        }
    ],
)
async def test_update_with_unnecessary_json_attrs(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test attributes when an expected key is missing."""

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.attributes["key"] == "some_json_value"
    assert entity_state.attributes["another_key"] == "another_json_value"
    assert "key_three" not in entity_state.attributes


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": 'echo \
                            {\
                                \\"top_level\\": {\
                                    \\"second_level\\": {\
                                        \\"key\\": \\"some_json_value\\",\
                                        \\"another_key\\": \\"another_json_value\\",\
                                        \\"key_three\\": \\"value_three\\"\
                                    }\
                                }\
                            }',
                        "json_attributes": ["key", "another_key", "key_three"],
                        "json_attributes_path": "$.top_level.second_level",
                    }
                }
            ]
        }
    ],
)
async def test_update_with_json_attrs_with_json_attrs_path(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test using json_attributes_path to select a different part of the json object as root."""

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.attributes["key"] == "some_json_value"
    assert entity_state.attributes["another_key"] == "another_json_value"
    assert entity_state.attributes["key_three"] == "value_three"
    assert "top_level" not in entity_state.attributes
    assert "second_level" not in entity_state.attributes


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "unique_id": "unique",
                        "command": "echo 0",
                    }
                },
                {
                    "sensor": {
                        "name": "Test",
                        "unique_id": "not-so-unique-anymore",
                        "command": "echo 1",
                    }
                },
                {
                    "sensor": {
                        "name": "Test",
                        "unique_id": "not-so-unique-anymore",
                        "command": "echo 2",
                    },
                },
            ]
        }
    ],
)
async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry, load_yaml_integration: None
) -> None:
    """Test unique_id option and if it only creates one sensor per id."""

    assert len(menuai.states.async_all()) == 2

    assert len(entity_registry.entities) == 2
    assert entity_registry.async_get_entity_id("sensor", "command_line", "unique")
    assert entity_registry.async_get_entity_id(
        "sensor", "command_line", "not-so-unique-anymore"
    )


async def test_updating_to_often(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling updating when command already running."""
    wait_till_event = asyncio.Event()
    wait_till_event.set()
    called = []

    class MockCommandSensor(CommandSensor):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update entity."""
            called.append(1)
            # Wait till event is set
            await wait_till_event.wait()

    with patch(
        "menuai.components.command_line.sensor.CommandSensor",
        side_effect=MockCommandSensor,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "sensor": {
                            "name": "Test",
                            "command": "echo 1",
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
        "Updating Command Line Sensor Test took longer than the scheduled update interval"
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
        "Updating Command Line Sensor Test took longer than the scheduled update interval"
        in caplog.text
    )


async def test_updating_manually(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling manual updating using menuai udate_entity service."""
    await setup.async_setup_component(menuai, HA_DOMAIN, {})
    called = []

    class MockCommandSensor(CommandSensor):
        """Mock entity that updates."""

        async def _async_update(self) -> None:
            """Update slow."""
            called.append(1)

    with patch(
        "menuai.components.command_line.sensor.CommandSensor",
        side_effect=MockCommandSensor,
    ):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "sensor": {
                            "name": "Test",
                            "command": "echo 1",
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
        {ATTR_ENTITY_ID: ["sensor.test"]},
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
                    "sensor": {
                        "name": "Test",
                        "command": "echo 2022-12-22T13:15:30Z",
                        "device_class": "timestamp",
                    }
                }
            ]
        }
    ],
)
async def test_scrape_sensor_device_timestamp(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test Command Line sensor with a device of type TIMESTAMP."""
    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "2022-12-22T13:15:30+00:00"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo January 17, 2022",
                        "device_class": "date",
                        "value_template": "{{ strptime(value, '%B %d, %Y').strftime('%Y-%m-%d') }}",
                    }
                }
            ]
        }
    ],
)
async def test_scrape_sensor_device_date(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test Command Line sensor with a device of type DATE."""
    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "2022-01-17"


async def test_template_not_error_when_data_is_none(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test command sensor with template not logging error when data is None."""

    with mock_asyncio_subprocess_run(returncode=1):
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "sensor": {
                            "name": "Test",
                            "command": "failed command",
                            "unit_of_measurement": "MB",
                            "value_template": "{{ (value.split('\t')[0]|int(0)/1000)|round(3) }}",
                        }
                    }
                ]
            },
        )
    await menuai.async_block_till_done()

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNKNOWN

    assert (
        "Template variable error: 'None' has no attribute 'split' when rendering"
        not in caplog.text
    )


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": 'echo { \\"key\\": \\"value\\" }',
                        "availability": '{{ "sensor.input1" | has_value }}',
                        "icon": 'mdi:{{ states("sensor.input1") }}',
                        "json_attributes": ["key"],
                    }
                }
            ]
        }
    ],
)
async def test_availability_json_attributes_without_value_template(
    menuai: menuai,
    load_yaml_integration: None,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test availability."""
    menuai.states.async_set("sensor.input1", "on")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "unknown"
    assert entity_state.attributes["key"] == "value"
    assert entity_state.attributes["icon"] == "mdi:on"

    menuai.states.async_set("sensor.input1", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"Not A Number"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Unable to parse output as JSON" not in caplog.text

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE
    assert "key" not in entity_state.attributes
    assert "icon" not in entity_state.attributes

    menuai.states.async_set("sensor.input1", "on")
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"Not A Number"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Unable to parse output as JSON" in caplog.text

    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)
    with mock_asyncio_subprocess_run(b'{ "key": "value" }'):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "unknown"
    assert entity_state.attributes["key"] == "value"
    assert entity_state.attributes["icon"] == "mdi:on"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo January 17, 2022",
                        "device_class": "date",
                        "value_template": "{{ strptime(value, '%B %d, %Y').strftime('%Y-%m-%d') }}",
                        "availability": '{{ states("sensor.input1")=="on" }}',
                        "icon": "mdi:o{{ 'n' if states('sensor.input1')=='on' else 'ff' }}",
                    }
                }
            ]
        }
    ],
)
async def test_availability_with_value_template(
    menuai: menuai,
    load_yaml_integration: None,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test availability."""

    menuai.states.async_set("sensor.input1", "on")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "2022-01-17"
    assert entity_state.attributes["icon"] == "mdi:on"

    menuai.states.async_set("sensor.input1", "off")
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"January 17, 2022"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE
    assert "icon" not in entity_state.attributes


async def test_template_render_with_availability_syntax_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test availability template render with syntax errors."""
    assert await setup.async_setup_component(
        menuai,
        "command_line",
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo {{ states.sensor.input_sensor.state }}",
                        "availability": "{{ what_the_heck == 2 }}",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.input_sensor", "1")
    await menuai.async_block_till_done()

    # Give time for template to load
    async_fire_time_changed(
        menuai,
        dt_util.utcnow() + timedelta(minutes=1),
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    # Sensors are unknown if never triggered
    state = menuai.states.get("sensor.test")
    assert state is not None
    assert state.state == "1"

    assert (
        "Error rendering availability template for sensor.test: UndefinedError: 'what_the_heck' is undefined"
        in caplog.text
    )


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo {{ states.sensor.input_sensor.state }}",
                        "availability": "{{ value|is_number}}",
                        "unit_of_measurement": " ",
                        "state_class": "measurement",
                    }
                }
            ]
        }
    ],
)
async def test_command_template_render_with_availability(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test command template is rendered properly with availability."""
    menuai.states.async_set("sensor.input_sensor", "sensor_value")

    # Give time for template to load
    async_fire_time_changed(
        menuai,
        dt_util.utcnow() + timedelta(minutes=1),
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE

    menuai.states.async_set("sensor.input_sensor", "1")

    # Give time for template to load
    async_fire_time_changed(
        menuai,
        dt_util.utcnow() + timedelta(minutes=1),
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == "1"


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "sensor": {
                        "name": "Test",
                        "command": "echo 0",
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
    error = "Error parsing value for sensor.test: 'x' is undefined"
    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"51\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error not in caplog.text

    entity_state = menuai.states.get("sensor.test")
    assert entity_state
    assert entity_state.state == STATE_UNAVAILABLE

    await menuai.async_block_till_done()
    with mock_asyncio_subprocess_run(b"50\n"):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert error in caplog.text
