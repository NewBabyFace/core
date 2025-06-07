"""Tests for Vodafone Station init."""

from unittest.mock import AsyncMock

from menuai.components.device_tracker import CONF_CONSIDER_HOME
from menuai.components.vodafone_station.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import setup_integration

from tests.common import MockConfigEntry


async def test_reload_config_entry_with_options(
    menuai: menuai,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the the config entry is reloaded with options."""
    await setup_integration(menuai, mock_config_entry)

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONSIDER_HOME: 37,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_CONSIDER_HOME: 37,
    }


async def test_unload_entry(
    menuai: menuai,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unloading the config entry."""
    await setup_integration(menuai, mock_config_entry)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
