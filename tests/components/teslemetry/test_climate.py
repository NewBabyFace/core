"""Test the Teslemetry climate platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import InvalidCommand
from teslemetry_stream import Signal

from menuai.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er

from . import assert_entities, reload_platform, setup_platform
from .const import (
    COMMAND_ERRORS,
    COMMAND_IGNORED_REASON,
    METADATA_NOSCOPE,
    VEHICLE_DATA_ALT,
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_climate(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_legacy: AsyncMock,
) -> None:
    """Tests that the climate entity is correct."""

    entry = await setup_platform(menuai, [Platform.CLIMATE])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    entity_id = "climate.test_climate"

    # Turn On and Set Temp
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TEMPERATURE: 20,
            ATTR_HVAC_MODE: HVACMode.HEAT_COOL,
        },
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.HEAT_COOL

    # Set Temp
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TEMPERATURE: 21,
        },
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 21

    # Set Preset
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_PRESET_MODE: "keep"},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == "keep"

    # Set Preset
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_PRESET_MODE: "off"},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == "off"

    # Turn Off
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.state == HVACMode.OFF

    entity_id = "climate.test_cabin_overheat_protection"

    # Turn On and Set Low
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TEMPERATURE: 30,
            ATTR_HVAC_MODE: HVACMode.FAN_ONLY,
        },
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 30
    assert state.state == HVACMode.FAN_ONLY

    # Set Temp Medium
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TEMPERATURE: 35,
        },
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 35

    # Set Temp High
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_TEMPERATURE: 40,
        },
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 40

    # Turn Off
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.state == HVACMode.OFF

    # Turn On
    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.state == HVACMode.COOL

    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_TEMPERATURE] == 40
    assert state.state == HVACMode.COOL

    # pytest raises ServiceValidationError
    with pytest.raises(
        ServiceValidationError,
        match="Cabin overheat protection does not support that temperature",
    ):
        # Invalid Temp
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 34},
            blocking=True,
        )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_climate_alt(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vehicle_data: AsyncMock,
    mock_legacy: AsyncMock,
) -> None:
    """Tests that the climate entity is correct."""

    mock_vehicle_data.return_value = VEHICLE_DATA_ALT
    entry = await setup_platform(menuai, [Platform.CLIMATE])
    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)


async def test_invalid_error(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Tests service error is handled."""

    await setup_platform(menuai, platforms=[Platform.CLIMATE])
    entity_id = "climate.test_climate"

    with (
        patch(
            "tesla_fleet_api.teslemetry.Vehicle.auto_conditioning_start",
            side_effect=InvalidCommand,
        ) as mock_on,
        pytest.raises(menuaiError) as error,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_on.assert_called_once()
    assert str(error.value) == snapshot(name="error")


@pytest.mark.parametrize("response", COMMAND_ERRORS)
async def test_errors(menuai: menuai, response: str) -> None:
    """Tests service reason is handled."""

    await setup_platform(menuai, platforms=[Platform.CLIMATE])
    entity_id = "climate.test_climate"

    with (
        patch(
            "tesla_fleet_api.teslemetry.Vehicle.auto_conditioning_start",
            return_value=response,
        ) as mock_on,
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_on.assert_called_once()


async def test_ignored_error(
    menuai: menuai,
) -> None:
    """Tests ignored error is handled."""

    await setup_platform(menuai, [Platform.CLIMATE])
    entity_id = "climate.test_climate"
    with patch(
        "tesla_fleet_api.teslemetry.Vehicle.auto_conditioning_start",
        return_value=COMMAND_IGNORED_REASON,
    ) as mock_on:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_on.assert_called_once()


async def test_climate_noscope(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_metadata: AsyncMock,
    mock_legacy: AsyncMock,
) -> None:
    """Tests that the climate entity is correct."""
    mock_metadata.return_value = METADATA_NOSCOPE

    entry = await setup_platform(menuai, [Platform.CLIMATE])

    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")

    entity_id = "climate.test_climate"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.HEAT_COOL},
            blocking=True,
        )

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 20},
            blocking=True,
        )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_select_streaming(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_vehicle_data: AsyncMock,
    mock_add_listener: AsyncMock,
) -> None:
    """Tests that the select entities with streaming are correct."""

    entry = await setup_platform(menuai, [Platform.CLIMATE])

    # Stream update
    mock_add_listener.send(
        {
            "vin": VEHICLE_DATA_ALT["response"]["vin"],
            "data": {
                Signal.INSIDE_TEMP: 26,
                Signal.HVAC_AC_ENABLED: True,
                Signal.CLIMATE_KEEPER_MODE: "ClimateKeeperModeOn",
                Signal.RIGHT_HAND_DRIVE: True,
                Signal.HVAC_LEFT_TEMPERATURE_REQUEST: 22,
                Signal.HVAC_RIGHT_TEMPERATURE_REQUEST: 21,
                Signal.CABIN_OVERHEAT_PROTECTION_MODE: "CabinOverheatProtectionModeStateOn",
                Signal.CABIN_OVERHEAT_PROTECTION_TEMPERATURE_LIMIT: 35,
            },
            "createdAt": "2024-10-04T10:45:17.537Z",
        }
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("climate.test_climate") == snapshot(
        name="climate.test_climate LHD"
    )

    await reload_platform(menuai, entry, [Platform.CLIMATE])

    # Assert the entities restored their values
    for entity_id in (
        "climate.test_climate",
        "climate.test_cabin_overheat_protection",
    ):
        assert menuai.states.get(entity_id) == snapshot(name=entity_id)
