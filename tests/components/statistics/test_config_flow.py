"""Test the Scrape config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import config_entries
from menuai.components.recorder import Recorder
from menuai.components.statistics import DOMAIN
from menuai.components.statistics.sensor import (
    CONF_KEEP_LAST_SAMPLE,
    CONF_MAX_AGE,
    CONF_PERCENTILE,
    CONF_PRECISION,
    CONF_SAMPLES_MAX_BUFFER_SIZE,
    CONF_STATE_CHARACTERISTIC,
    DEFAULT_NAME,
    STAT_AVERAGE_LINEAR,
    STAT_COUNT,
    STAT_VALUE_MAX,
)
from menuai.const import CONF_ENTITY_ID, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


async def test_form_sensor(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form for sensor."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ENTITY_ID: "sensor.test_monitored",
        CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
        CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        CONF_KEEP_LAST_SAMPLE: False,
        CONF_PERCENTILE: 50.0,
        CONF_PRECISION: 2.0,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_binary_sensor(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the form for binary sensor."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "binary_sensor.test_monitored",
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATE_CHARACTERISTIC: STAT_COUNT,
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ENTITY_ID: "binary_sensor.test_monitored",
        CONF_STATE_CHARACTERISTIC: STAT_COUNT,
        CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
        CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        CONF_KEEP_LAST_SAMPLE: False,
        CONF_PERCENTILE: 50.0,
        CONF_PRECISION: 2.0,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test options flow."""

    result = await menuai.config_entries.options.async_init(loaded_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SAMPLES_MAX_BUFFER_SIZE: 25.0,
            CONF_MAX_AGE: {"hours": 16, "minutes": 0, "seconds": 0},
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ENTITY_ID: "sensor.test_monitored",
        CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        CONF_SAMPLES_MAX_BUFFER_SIZE: 25.0,
        CONF_MAX_AGE: {"hours": 16, "minutes": 0, "seconds": 0},
        CONF_KEEP_LAST_SAMPLE: False,
        CONF_PERCENTILE: 50.0,
        CONF_PRECISION: 2.0,
    }

    await menuai.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(menuai.states.async_all()) == 2

    state = menuai.states.get("sensor.statistical_characteristic")
    assert state is not None


async def test_validation_options(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test validation."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await menuai.async_block_till_done()

    assert result["step_id"] == "options"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "missing_max_age_or_sampling_size"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KEEP_LAST_SAMPLE: True, CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0},
    )
    await menuai.async_block_till_done()

    assert result["step_id"] == "options"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "missing_keep_last_sample"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ENTITY_ID: "sensor.test_monitored",
        CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
        CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
        CONF_KEEP_LAST_SAMPLE: False,
        CONF_PERCENTILE: 50.0,
        CONF_PRECISION: 2.0,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_entry_already_exist(
    menuai: menuai, loaded_entry: MockConfigEntry
) -> None:
    """Test abort when entry already exist."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
        },
    )
    await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 5, "seconds": 5},
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "user_input",
    [
        (
            {
                CONF_SAMPLES_MAX_BUFFER_SIZE: 10.0,
                CONF_KEEP_LAST_SAMPLE: False,
                CONF_PERCENTILE: 50,
                CONF_PRECISION: 2,
            }
        ),
        (
            {
                CONF_KEEP_LAST_SAMPLE: False,
                CONF_PERCENTILE: 50,
                CONF_PRECISION: 2,
            }
        ),
    ],
    ids=("success", "missing_size_and_age"),
)
async def test_config_flow_preview_success(
    recorder_mock: Recorder,
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    user_input: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the config flow preview."""
    client = await menuai_ws_client(menuai)

    # add state for the tests
    menuai.states.async_set("sensor.test_monitored", "16")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
        },
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATE_CHARACTERISTIC: STAT_VALUE_MAX,
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "options"
    assert result["errors"] is None
    assert result["preview"] == "statistics"

    await client.send_json_auto_id(
        {
            "type": "statistics/start_preview",
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
    recorder_mock: Recorder,
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the options flow preview."""
    client = await menuai_ws_client(menuai)

    # add state for the tests
    menuai.states.async_set("sensor.test_monitored", "16")

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
            CONF_STATE_CHARACTERISTIC: STAT_VALUE_MAX,
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
            CONF_KEEP_LAST_SAMPLE: False,
            CONF_PERCENTILE: 50.0,
            CONF_PRECISION: 2.0,
        },
        title=DEFAULT_NAME,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None
    assert result["preview"] == "statistics"

    await client.send_json_auto_id(
        {
            "type": "statistics/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "options_flow",
            "user_input": {
                CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
                CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
                CONF_KEEP_LAST_SAMPLE: False,
                CONF_PERCENTILE: 50.0,
                CONF_PRECISION: 2.0,
            },
        }
    )

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None

    msg = await client.receive_json()
    assert msg["event"] == snapshot
    assert len(menuai.states.async_all()) == 2

    # add state for the tests
    menuai.states.async_set("sensor.test_monitored", "20")
    await menuai.async_block_till_done()

    msg = await client.receive_json()
    assert msg["event"] == snapshot(name="updated")


async def test_options_flow_sensor_preview_config_entry_removed(
    recorder_mock: Recorder, menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test the option flow preview where the config entry is removed."""
    client = await menuai_ws_client(menuai)

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_NAME: DEFAULT_NAME,
            CONF_ENTITY_ID: "sensor.test_monitored",
            CONF_STATE_CHARACTERISTIC: STAT_AVERAGE_LINEAR,
            CONF_SAMPLES_MAX_BUFFER_SIZE: 20.0,
            CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
            CONF_KEEP_LAST_SAMPLE: False,
            CONF_PERCENTILE: 50.0,
            CONF_PRECISION: 2.0,
        },
        title=DEFAULT_NAME,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None
    assert result["preview"] == "statistics"

    await menuai.config_entries.async_remove(config_entry.entry_id)

    await client.send_json_auto_id(
        {
            "type": "statistics/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "options_flow",
            "user_input": {
                CONF_SAMPLES_MAX_BUFFER_SIZE: 25.0,
                CONF_MAX_AGE: {"hours": 8, "minutes": 0, "seconds": 0},
                CONF_KEEP_LAST_SAMPLE: False,
                CONF_PERCENTILE: 50.0,
                CONF_PRECISION: 2.0,
            },
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {
        "code": "home_assistant_error",
        "message": "Config entry not found",
    }
