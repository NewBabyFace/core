"""Test the Fibaro cover platform."""

from unittest.mock import Mock, patch

from menuai.components.cover import CoverState
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry


async def test_cover_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_cover: Mock,
    mock_room: Mock,
) -> None:
    """Test that the cover creates an entity."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_cover]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.COVER]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        entry = entity_registry.async_get("cover.room_1_test_cover_3")
        assert entry
        assert entry.unique_id == "hc2_111111.3"
        assert entry.original_name == "Room 1 Test cover"


async def test_cover_opening(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_cover: Mock,
    mock_room: Mock,
) -> None:
    """Test that the cover opening state is reported."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_cover]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.COVER]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        assert menuai.states.get("cover.room_1_test_cover_3").state == CoverState.OPENING


async def test_cover_opening_closing_none(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_cover: Mock,
    mock_room: Mock,
) -> None:
    """Test that the cover opening closing states return None if not available."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_cover.state.has_value = False
    mock_fibaro_client.read_devices.return_value = [mock_cover]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.COVER]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        assert menuai.states.get("cover.room_1_test_cover_3").state == CoverState.OPEN


async def test_cover_closing(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_cover: Mock,
    mock_room: Mock,
) -> None:
    """Test that the cover closing state is reported."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_cover.state.str_value.return_value = "closing"
    mock_fibaro_client.read_devices.return_value = [mock_cover]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.COVER]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        assert menuai.states.get("cover.room_1_test_cover_3").state == CoverState.CLOSING
