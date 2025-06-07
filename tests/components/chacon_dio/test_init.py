"""Test the Dio Chacon Cover init."""

from unittest.mock import AsyncMock

from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_cover_unload_entry(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the creation and values of the Dio Chacon covers."""

    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_dio_chacon_client.disconnect.assert_called()


async def test_cover_shutdown_event(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the creation and values of the Dio Chacon covers."""

    await setup_integration(menuai, mock_config_entry)

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    mock_dio_chacon_client.disconnect.assert_called()
