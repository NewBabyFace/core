"""Test the Times of the Day config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.tod.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, get_schema_suggested_value


@pytest.mark.parametrize("platform", ["sensor"])
async def test_config_flow(menuai: menuai, platform) -> None:
    """Test the config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.tod.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "after_time": "10:00",
                "before_time": "18:00",
                "name": "My tod",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My tod"
    assert result["data"] == {}
    assert result["options"] == {
        "after_time": "10:00",
        "before_time": "18:00",
        "name": "My tod",
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "after_time": "10:00",
        "before_time": "18:00",
        "name": "My tod",
    }
    assert config_entry.title == "My tod"


@pytest.mark.freeze_time("2022-03-16 17:37:00", tz_offset=-7)
async def test_options(menuai: menuai) -> None:
    """Test reconfiguring."""
    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "after_time": "10:00",
            "before_time": "18:05",
            "name": "My tod",
        },
        title="My tod",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_schema_suggested_value(schema, "after_time") == "10:00"
    assert get_schema_suggested_value(schema, "before_time") == "18:05"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "after_time": "10:00",
            "before_time": "17:05",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "after_time": "10:00",
        "before_time": "17:05",
        "name": "My tod",
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        "after_time": "10:00",
        "before_time": "17:05",
        "name": "My tod",
    }
    assert config_entry.title == "My tod"

    # Check config entry is reloaded with new options
    await menuai.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(menuai.states.async_all()) == 1

    # Check the state of the entity has changed as expected
    state = menuai.states.get("binary_sensor.my_tod")
    assert state.state == "off"
    assert state.attributes["after"] == "2022-03-16T10:00:00-07:00"
    assert state.attributes["before"] == "2022-03-16T17:05:00-07:00"
