"""Test the Advantage Air Climate Platform."""

from unittest.mock import AsyncMock

from advantage_air import ApiError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.advantage_air.climate import ADVANTAGE_AIR_MYAUTO
from menuai.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_AUTO,
    FAN_LOW,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er

from . import add_mock_config


async def test_climate_myzone_main(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate platform main entity."""

    await add_mock_config(menuai)

    # Test MyZone main climate entity
    entity_id = "climate.myzone"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes.get(ATTR_MIN_TEMP) == 16
    assert state.attributes.get(ATTR_MAX_TEMP) == 32
    assert state.attributes.get(ATTR_TEMPERATURE) == 24
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 25

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1"

    # Test setting HVAC Mode

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.FAN_ONLY},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning Off with HVAC Mode
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_FAN_MODE: FAN_LOW},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test changing Temperature
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 25},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning On
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning Off
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Change Preset
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_PRESET_MODE: ADVANTAGE_AIR_MYAUTO},
        blocking=True,
    )
    mock_update.assert_called_once()
    assert mock_update.call_args[0][0] == snapshot(name=f"{entity_id}-preset")
    mock_update.reset_mock()

    # Test setting HEAT COOL when its not supported
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.HEAT_COOL},
            blocking=True,
        )


async def test_climate_myzone_zone(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
) -> None:
    """Test climate platform myzone zone entity."""

    await add_mock_config(menuai)

    # Test Climate Zone Entity
    entity_id = "climate.myzone_zone_open_with_sensor"
    state = menuai.states.get(entity_id)
    assert state
    assert state.attributes.get(ATTR_MIN_TEMP) == 16
    assert state.attributes.get(ATTR_MAX_TEMP) == 32
    assert state.attributes.get(ATTR_TEMPERATURE) == 24
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 25

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01"

    # Test Climate Zone On
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.FAN_ONLY},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Climate Zone Off
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 25},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()


async def test_climate_myauto_main(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate platform zone entity."""

    await add_mock_config(menuai)

    # Test MyAuto Climate Entity
    entity_id = "climate.myauto"
    assert menuai.states.get(entity_id) == snapshot(name=entity_id)

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac3"

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TARGET_TEMP_LOW: 21,
            ATTR_TARGET_TEMP_HIGH: 23,
        },
        blocking=True,
    )
    mock_update.assert_called_once()
    assert mock_update.call_args[0][0] == snapshot(name=f"{entity_id}-settemp")
    mock_update.reset_mock()

    # Test AutoFanMode
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_FAN_MODE: FAN_AUTO},
        blocking=True,
    )
    mock_update.assert_called_once()
    assert mock_update.call_args[0][0] == snapshot(name=f"{entity_id}-fanmode")


async def test_climate_async_failed_update(
    menuai: menuai,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
) -> None:
    """Test climate change failure."""

    mock_update.side_effect = ApiError
    await add_mock_config(menuai)
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ["climate.myzone"], ATTR_TEMPERATURE: 25},
            blocking=True,
        )

    mock_update.assert_called_once()
