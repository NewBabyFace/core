"""Test init methods."""

from unittest.mock import Mock, patch

from menuai.const import Platform
from menuai.core import menuai

from .conftest import init_integration

from tests.common import MockConfigEntry


async def test_unload_integration(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test unload integration stops state listener."""
    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        await init_integration(menuai, mock_config_entry)
        # Act
        await menuai.config_entries.async_unload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
        # Assert
        assert mock_fibaro_client.unregister_update_handler.call_count == 1
