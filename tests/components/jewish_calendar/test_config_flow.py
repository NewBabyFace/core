"""Test the Jewish calendar config flow."""

from unittest.mock import AsyncMock

from menuai import config_entries, setup
from menuai.components.jewish_calendar.const import (
    CONF_CANDLE_LIGHT_MINUTES,
    CONF_DIASPORA,
    CONF_HAVDALAH_OFFSET_MINUTES,
    DEFAULT_CANDLE_LIGHT,
    DEFAULT_DIASPORA,
    DEFAULT_LANGUAGE,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    CONF_ELEVATION,
    CONF_LANGUAGE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_TIME_ZONE,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_step_user(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test user config."""
    await setup.async_setup_component(menuai, "persistent_notification", {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DIASPORA: DEFAULT_DIASPORA, CONF_LANGUAGE: DEFAULT_LANGUAGE},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY

    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 1

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data[CONF_DIASPORA] == DEFAULT_DIASPORA
    assert entries[0].data[CONF_LANGUAGE] == DEFAULT_LANGUAGE
    assert entries[0].data[CONF_LATITUDE] == menuai.config.latitude
    assert entries[0].data[CONF_LONGITUDE] == menuai.config.longitude
    assert entries[0].data[CONF_ELEVATION] == menuai.config.elevation
    assert entries[0].data[CONF_TIME_ZONE] == menuai.config.time_zone


async def test_single_instance_allowed(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test we abort if already setup."""
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"


async def test_options(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test updating options."""
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CANDLE_LIGHT_MINUTES: 25,
            CONF_HAVDALAH_OFFSET_MINUTES: 34,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].options[CONF_CANDLE_LIGHT_MINUTES] == 25
    assert entries[0].options[CONF_HAVDALAH_OFFSET_MINUTES] == 34


async def test_options_reconfigure(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test that updating the options of the Jewish Calendar integration triggers a value update."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert CONF_CANDLE_LIGHT_MINUTES not in config_entry.options

    # Update the CONF_CANDLE_LIGHT_MINUTES option to a new value
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CANDLE_LIGHT_MINUTES: DEFAULT_CANDLE_LIGHT + 1,
        },
    )
    assert result["result"]

    # The value of the "upcoming_shabbat_candle_lighting" sensor should be the new value
    assert config_entry.options[CONF_CANDLE_LIGHT_MINUTES] == DEFAULT_CANDLE_LIGHT + 1


async def test_reconfigure(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test starting a reconfigure flow."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # init user flow
    result = await config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # success
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DIASPORA: not DEFAULT_DIASPORA,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_DIASPORA] is not DEFAULT_DIASPORA
