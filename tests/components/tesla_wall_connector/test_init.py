"""Test the Tesla Wall Connector config flow."""

from tesla_wall_connector.exceptions import WallConnectorConnectionError

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import create_wall_connector_entry, get_lifetime_mock, get_vitals_mock


async def test_init_success(menuai: menuai) -> None:
    """Test setup and that we get the device info, including firmware version."""

    entry = await create_wall_connector_entry(
        menuai, vitals_data=get_vitals_mock(), lifetime_data=get_lifetime_mock()
    )

    assert entry.state is ConfigEntryState.LOADED


async def test_init_while_offline(menuai: menuai) -> None:
    """Test init with the wall connector offline."""
    entry = await create_wall_connector_entry(
        menuai, side_effect=WallConnectorConnectionError
    )

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_unload(menuai: menuai) -> None:
    """Config entry can be unloaded."""

    entry = await create_wall_connector_entry(
        menuai, vitals_data=get_vitals_mock(), lifetime_data=get_lifetime_mock()
    )
    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
