"""Tests for the BSB-Lan climate platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from bsblan import BSBLANError
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_ECO,
    PRESET_NONE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

ENTITY_ID = "climate.bsb_lan"


async def test_celsius_fahrenheit(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test Celsius and Fahrenheit temperature units."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_climate_entity_properties(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the climate entity properties."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)

    # Test target_temperature
    mock_target_temp = MagicMock()
    mock_target_temp.value = 23.5
    mock_bsblan.state.return_value.target_temperature = mock_target_temp

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_ID)
    assert state.attributes["temperature"] == 23.5

    # Test hvac_mode
    mock_hvac_mode = MagicMock()
    mock_hvac_mode.value = HVACMode.AUTO
    mock_bsblan.state.return_value.hvac_mode = mock_hvac_mode

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.AUTO

    # Test preset_mode
    mock_hvac_mode.value = PRESET_ECO

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_ID)
    assert state.attributes["preset_mode"] == PRESET_ECO


@pytest.mark.parametrize(
    "mode",
    [HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF],
)
async def test_async_set_hvac_mode(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mode: HVACMode,
) -> None:
    """Test setting HVAC mode via service call."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    # Call the service to set HVAC mode
    await menuai.services.async_call(
        domain=CLIMATE_DOMAIN,
        service=SERVICE_SET_HVAC_MODE,
        service_data={ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: mode},
        blocking=True,
    )

    # Assert that the thermostat method was called
    mock_bsblan.thermostat.assert_called_once_with(hvac_mode=mode)
    mock_bsblan.thermostat.reset_mock()


@pytest.mark.parametrize(
    ("hvac_mode", "preset_mode"),
    [
        (HVACMode.AUTO, PRESET_ECO),
        (HVACMode.AUTO, PRESET_NONE),
    ],
)
async def test_async_set_preset_mode_succes(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    hvac_mode: HVACMode,
    preset_mode: str,
) -> None:
    """Test setting preset mode via service call."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    # patch hvac_mode
    mock_hvac_mode = MagicMock()
    mock_hvac_mode.value = hvac_mode
    mock_bsblan.state.return_value.hvac_mode = mock_hvac_mode

    # Attempt to set the preset mode
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PRESET_MODE: preset_mode},
        blocking=True,
    )
    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    ("hvac_mode", "preset_mode"),
    [
        (
            HVACMode.HEAT,
            PRESET_ECO,
        )
    ],
)
async def test_async_set_preset_mode_error(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    hvac_mode: HVACMode,
    preset_mode: str,
) -> None:
    """Test setting preset mode via service call."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    # patch hvac_mode
    mock_hvac_mode = MagicMock()
    mock_hvac_mode.value = hvac_mode
    mock_bsblan.state.return_value.hvac_mode = mock_hvac_mode

    # Attempt to set the preset mode
    error_message = "Preset mode can only be set when HVAC mode is set to 'auto'"
    with pytest.raises(menuaiError, match=error_message):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PRESET_MODE: preset_mode},
            blocking=True,
        )


@pytest.mark.parametrize(
    ("target_temp"),
    [
        (8.0),  # Min temperature
        (15.0),  # Mid-range temperature
        (20.0),  # Max temperature
    ],
)
async def test_async_set_temperature(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    target_temp: float,
) -> None:
    """Test setting temperature via service call."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    await menuai.services.async_call(
        domain=CLIMATE_DOMAIN,
        service=SERVICE_SET_TEMPERATURE,
        service_data={ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: target_temp},
        blocking=True,
    )
    # Assert that the thermostat method was called with the correct temperature
    mock_bsblan.thermostat.assert_called_once_with(target_temperature=target_temp)


async def test_async_set_data(
    menuai: menuai,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting data via service calls."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.CLIMATE])

    # Test setting temperature
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 19},
        blocking=True,
    )
    mock_bsblan.thermostat.assert_called_once_with(target_temperature=19)
    mock_bsblan.thermostat.reset_mock()

    # Test setting HVAC mode
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    mock_bsblan.thermostat.assert_called_once_with(hvac_mode=HVACMode.HEAT)
    mock_bsblan.thermostat.reset_mock()

    # Patch HVAC mode to AUTO
    mock_hvac_mode = MagicMock()
    mock_hvac_mode.value = HVACMode.AUTO
    mock_bsblan.state.return_value.hvac_mode = mock_hvac_mode

    # Test setting preset mode to ECO
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
        blocking=True,
    )
    mock_bsblan.thermostat.assert_called_once_with(hvac_mode=PRESET_ECO)
    mock_bsblan.thermostat.reset_mock()

    # Test setting preset mode to NONE
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PRESET_MODE: PRESET_NONE},
        blocking=True,
    )
    mock_bsblan.thermostat.assert_called_once()
    mock_bsblan.thermostat.reset_mock()

    # Test error handling
    mock_bsblan.thermostat.side_effect = BSBLANError("Test error")
    error_message = "An error occurred while updating the BSBLAN device"
    with pytest.raises(menuaiError, match=error_message):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 20},
            blocking=True,
        )
