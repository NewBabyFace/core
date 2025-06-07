"""Test the Fibaro climate platform."""

from unittest.mock import Mock, patch

from menuai.components.climate import ClimateEntityFeature, HVACMode
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry


async def test_climate_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat: Mock,
    mock_room: Mock,
) -> None:
    """Test that the climate creates an entity."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        entry = entity_registry.async_get("climate.room_1_test_climate_4")
        assert entry
        assert entry.unique_id == "hc2_111111.4"
        assert entry.original_name == "Room 1 Test climate"
        assert entry.supported_features == (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.PRESET_MODE
        )


async def test_hvac_mode_preset(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat: Mock,
    mock_room: Mock,
) -> None:
    """Test that the climate state is auto when a preset is selected."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("climate.room_1_test_climate_4")
        assert state.state == HVACMode.AUTO
        assert state.attributes["preset_mode"] == "CustomerSpecific"


async def test_hvac_mode_heat(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat: Mock,
    mock_room: Mock,
) -> None:
    """Test that the preset mode is None if a hvac mode is active."""

    # Arrange
    mock_thermostat.thermostat_mode = "Heat"
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("climate.room_1_test_climate_4")
        assert state.state == HVACMode.HEAT
        assert state.attributes["preset_mode"] is None


async def test_set_hvac_mode(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat: Mock,
    mock_room: Mock,
) -> None:
    """Test that set_hvac_mode() works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        await menuai.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": "climate.room_1_test_climate_4", "hvac_mode": HVACMode.HEAT},
            blocking=True,
        )

        # Assert
        mock_thermostat.execute_action.assert_called_once()


async def test_hvac_mode_with_operation_mode_support(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_with_operating_mode: Mock,
    mock_room: Mock,
) -> None:
    """Test that operating mode works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat_with_operating_mode]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("climate.room_1_test_climate_6")
        assert state.state == HVACMode.AUTO


async def test_set_hvac_mode_with_operation_mode_support(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_with_operating_mode: Mock,
    mock_room: Mock,
) -> None:
    """Test that set_hvac_mode() works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_thermostat_with_operating_mode]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        await menuai.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": "climate.room_1_test_climate_6", "hvac_mode": HVACMode.HEAT},
            blocking=True,
        )

        # Assert
        mock_thermostat_with_operating_mode.execute_action.assert_called_once()


async def test_fan_mode(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_parent: Mock,
    mock_thermostat_with_operating_mode: Mock,
    mock_fan_device: Mock,
    mock_room: Mock,
) -> None:
    """Test that operating mode works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [
        mock_thermostat_parent,
        mock_thermostat_with_operating_mode,
        mock_fan_device,
    ]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("climate.room_1_test_climate_6")
        assert state.attributes["fan_mode"] == "low"
        assert state.attributes["fan_modes"] == ["off", "low", "auto_high"]


async def test_set_fan_mode(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_parent: Mock,
    mock_thermostat_with_operating_mode: Mock,
    mock_fan_device: Mock,
    mock_room: Mock,
) -> None:
    """Test that set_fan_mode() works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [
        mock_thermostat_parent,
        mock_thermostat_with_operating_mode,
        mock_fan_device,
    ]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        await menuai.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": "climate.room_1_test_climate_6", "fan_mode": "off"},
            blocking=True,
        )

        # Assert
        mock_fan_device.execute_action.assert_called_once()


async def test_target_temperature(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_parent: Mock,
    mock_thermostat_with_operating_mode: Mock,
    mock_fan_device: Mock,
    mock_room: Mock,
) -> None:
    """Test that operating mode works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [
        mock_thermostat_parent,
        mock_thermostat_with_operating_mode,
        mock_fan_device,
    ]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        # Assert
        state = menuai.states.get("climate.room_1_test_climate_6")
        assert state.attributes["temperature"] == 23


async def test_set_target_temperature(
    menuai: menuai,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_thermostat_parent: Mock,
    mock_thermostat_with_operating_mode: Mock,
    mock_fan_device: Mock,
    mock_room: Mock,
) -> None:
    """Test that set_fan_mode() works."""

    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [
        mock_thermostat_parent,
        mock_thermostat_with_operating_mode,
        mock_fan_device,
    ]

    with patch("menuai.components.fibaro.PLATFORMS", [Platform.CLIMATE]):
        # Act
        await init_integration(menuai, mock_config_entry)
        await menuai.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": "climate.room_1_test_climate_6", "temperature": 25.5},
            blocking=True,
        )

        # Assert
        mock_thermostat_with_operating_mode.execute_action.assert_called_once()
