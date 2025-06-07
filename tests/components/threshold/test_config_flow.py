"""Test the Threshold config flow."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import config_entries
from menuai.components.threshold.const import DOMAIN
from menuai.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, get_schema_suggested_value
from tests.typing import WebSocketGenerator


async def test_config_flow(menuai: menuai) -> None:
    """Test the config flow."""
    input_sensor = "sensor.input"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.threshold.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "entity_id": input_sensor,
                "lower": -2,
                "upper": 0.0,
                "name": "My threshold sensor",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My threshold sensor"
    assert result["data"] == {}
    assert result["options"] == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": -2.0,
        "name": "My threshold sensor",
        "upper": 0.0,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": -2.0,
        "name": "My threshold sensor",
        "upper": 0.0,
    }
    assert config_entry.title == "My threshold sensor"


@pytest.mark.parametrize(("extra_input_data", "error"), [({}, "need_lower_upper")])
async def test_fail(menuai: menuai, extra_input_data, error) -> None:
    """Test not providing lower or upper limit fails."""
    input_sensor = "sensor.input"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "entity_id": input_sensor,
            "name": "My threshold sensor",
            **extra_input_data,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_options(menuai: menuai) -> None:
    """Test reconfiguring."""
    input_sensor = "sensor.input"
    menuai.states.async_set(input_sensor, "10")

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": input_sensor,
            "hysteresis": 0.0,
            "lower": -2.0,
            "name": "My threshold",
            "upper": None,
        },
        title="My threshold",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_schema_suggested_value(schema, "hysteresis") == 0.0
    assert get_schema_suggested_value(schema, "lower") == -2.0
    assert get_schema_suggested_value(schema, "upper") is None

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "entity_id": input_sensor,
            "hysteresis": 0.0,
            "upper": 20.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": None,
        "name": "My threshold",
        "upper": 20.0,
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": None,
        "name": "My threshold",
        "upper": 20.0,
    }
    assert config_entry.title == "My threshold"

    # Check config entry is reloaded with new options
    await menuai.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(menuai.states.async_all()) == 2

    # Check the state of the entity has changed as expected
    state = menuai.states.get("binary_sensor.my_threshold")
    assert state.state == "off"
    assert state.attributes["type"] == "upper"


@pytest.mark.parametrize(
    "user_input",
    [
        (
            {
                "name": "Test Sensor",
                "entity_id": "sensor.test_monitored",
                "hysteresis": 0.0,
                "lower": 20.0,
            }
        ),
        (
            {
                "name": "Test Sensor",
                "entity_id": "sensor.test_monitored",
                "hysteresis": 0.0,
            }
        ),
        (
            {
                "name": "",
                "entity_id": "",
                "hysteresis": 0.0,
                "lower": 20.0,
            }
        ),
    ],
    ids=("success", "missing_upper_lower", "missing_entity_id"),
)
async def test_config_flow_preview_success(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    user_input: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the config flow preview."""
    client = await menuai_ws_client(menuai)

    # add state for the tests
    menuai.states.async_set(
        "sensor.test_monitored",
        16,
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None
    assert result["preview"] == "threshold"

    await client.send_json_auto_id(
        {
            "type": "threshold/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "config_flow",
            "user_input": user_input,
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None

    msg = await client.receive_json()
    assert msg["event"] == snapshot
    assert len(menuai.states.async_all()) == 1


async def test_options_flow_preview(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the options flow preview."""
    client = await menuai_ws_client(menuai)

    # add state for the tests
    menuai.states.async_set(
        "sensor.test_monitored",
        16,
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": "sensor.test_monitored",
            "hysteresis": 0.0,
            "lower": 20.0,
            "name": "Test Sensor",
            "upper": None,
        },
        title="Test Sensor",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None
    assert result["preview"] == "threshold"

    await client.send_json_auto_id(
        {
            "type": "threshold/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "options_flow",
            "user_input": {
                "name": "Test Sensor",
                "entity_id": "sensor.test_monitored",
                "hysteresis": 0.0,
                "lower": 20.0,
            },
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None

    msg = await client.receive_json()
    assert msg["event"] == snapshot
    assert len(menuai.states.async_all()) == 2


async def test_options_flow_sensor_preview_config_entry_removed(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test the option flow preview where the config entry is removed."""
    client = await menuai_ws_client(menuai)

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": "sensor.test_monitored",
            "hysteresis": 0.0,
            "lower": 20.0,
            "name": "Test Sensor",
            "upper": None,
        },
        title="Test Sensor",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None
    assert result["preview"] == "threshold"

    await menuai.config_entries.async_remove(config_entry.entry_id)

    await client.send_json_auto_id(
        {
            "type": "threshold/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "options_flow",
            "user_input": {
                "name": "Test Sensor",
                "entity_id": "sensor.test_monitored",
                "hysteresis": 0.0,
                "lower": 20.0,
            },
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {
        "code": "home_assistant_error",
        "message": "Config entry not found",
    }
