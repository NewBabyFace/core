"""Test the Fibaro light platform."""

from unittest.mock import Mock, patch

from menuai.components.light import DOMAIN as LIGHT_DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry


async def test_light_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test that the light creates an entity."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        entry = entity_registry.async_get("light.room_1_test_light_3")
        assert entry
        assert entry.unique_id == "hc2_111111.3"
        assert entry.original_name == "Room 1 Test light"


async def test_light_brightness(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test that the light brightness value is translated."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("light.room_1_test_light_3")
        assert state.attributes["brightness"] == 51
        assert state.state == "on"


async def test_light_turn_off(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test activate scene is called."""
    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        await init_integration(menuai, mock_config_entry)
        # Act
        await menuai.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "light.room_1_test_light_3"},
            blocking=True,
        )
        # Assert
        assert mock_light.execute_action.call_count == 1
