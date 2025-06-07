"""Test the Waze Travel Time config flow."""

import pytest

from menuai import config_entries
from menuai.components.waze_travel_time.config_flow import WazeConfigFlow
from menuai.components.waze_travel_time.const import (
    CONF_AVOID_FERRIES,
    CONF_AVOID_SUBSCRIPTION_ROADS,
    CONF_AVOID_TOLL_ROADS,
    CONF_DESTINATION,
    CONF_EXCL_FILTER,
    CONF_INCL_FILTER,
    CONF_ORIGIN,
    CONF_REALTIME,
    CONF_UNITS,
    CONF_VEHICLE_TYPE,
    DEFAULT_NAME,
    DEFAULT_OPTIONS,
    DOMAIN,
    IMPERIAL_UNITS,
)
from menuai.const import CONF_NAME, CONF_REGION
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import CONFIG_FLOW_USER_INPUT, MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("validate_config_entry")
async def test_minimum_fields(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG_FLOW_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_NAME
    assert result2["data"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ORIGIN: "location1",
        CONF_DESTINATION: "location2",
        CONF_REGION: "US",
    }


@pytest.mark.usefixtures("mock_update")
async def test_reconfigure(menuai: menuai) -> None:
    """Test reconfigure flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        options=DEFAULT_OPTIONS,
        version=WazeConfigFlow.VERSION,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    reconfigure_result = await entry.start_reconfigure_flow(menuai)
    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["step_id"] == "user"

    user_step_result = await menuai.config_entries.flow.async_configure(
        reconfigure_result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_ORIGIN: "location3",
            CONF_DESTINATION: "location4",
            CONF_REGION: "us",
        },
    )
    assert user_step_result["type"] is FlowResultType.ABORT
    assert user_step_result["reason"] == "reconfigure_successful"
    await menuai.async_block_till_done()

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.data == {
        CONF_NAME: DEFAULT_NAME,
        CONF_ORIGIN: "location3",
        CONF_DESTINATION: "location4",
        CONF_REGION: "US",
    }


async def test_options(menuai: menuai) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        options=DEFAULT_OPTIONS,
        version=WazeConfigFlow.VERSION,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id, data=None)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AVOID_FERRIES: True,
            CONF_AVOID_SUBSCRIPTION_ROADS: True,
            CONF_AVOID_TOLL_ROADS: True,
            CONF_EXCL_FILTER: ["exclude"],
            CONF_INCL_FILTER: ["include"],
            CONF_REALTIME: False,
            CONF_UNITS: IMPERIAL_UNITS,
            CONF_VEHICLE_TYPE: "taxi",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"] == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: ["exclude"],
        CONF_INCL_FILTER: ["include"],
        CONF_REALTIME: False,
        CONF_UNITS: IMPERIAL_UNITS,
        CONF_VEHICLE_TYPE: "taxi",
    }

    assert entry.options == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: ["exclude"],
        CONF_INCL_FILTER: ["include"],
        CONF_REALTIME: False,
        CONF_UNITS: IMPERIAL_UNITS,
        CONF_VEHICLE_TYPE: "taxi",
    }


@pytest.mark.usefixtures("validate_config_entry")
async def test_dupe(menuai: menuai) -> None:
    """Test setting up the same entry data twice is OK."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG_FLOW_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG_FLOW_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("invalidate_config_entry")
async def test_invalid_config_entry(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG_FLOW_USER_INPUT,
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}

    assert "Error trying to validate entry" in caplog.text


@pytest.mark.usefixtures("mock_update")
async def test_reset_filters(menuai: menuai) -> None:
    """Test resetting inclusive and exclusive filters to empty string."""
    options = {**DEFAULT_OPTIONS}
    options[CONF_INCL_FILTER] = ["test"]
    options[CONF_EXCL_FILTER] = ["test"]
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        options=options,
        entry_id="test",
        version=WazeConfigFlow.VERSION,
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(
        config_entry.entry_id, data=None
    )

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AVOID_FERRIES: True,
            CONF_AVOID_SUBSCRIPTION_ROADS: True,
            CONF_AVOID_TOLL_ROADS: True,
            CONF_REALTIME: False,
            CONF_UNITS: IMPERIAL_UNITS,
            CONF_VEHICLE_TYPE: "taxi",
        },
    )

    assert config_entry.options == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: [""],
        CONF_INCL_FILTER: [""],
        CONF_REALTIME: False,
        CONF_UNITS: IMPERIAL_UNITS,
        CONF_VEHICLE_TYPE: "taxi",
    }
