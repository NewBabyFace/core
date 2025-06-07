"""Test the BryantEvolutionClient type."""

from collections.abc import Generator
from datetime import timedelta
import logging
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.bryant_evolution.climate import SCAN_INTERVAL
from menuai.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

_LOGGER = logging.getLogger(__name__)


async def trigger_polling(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Trigger a polling event."""
    freezer.tick(SCAN_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()


async def test_setup_integration_success(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_evolution_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that an instance can be constructed."""
    await snapshot_platform(
        menuai, entity_registry, snapshot, mock_evolution_entry.entry_id
    )


async def test_set_temperature_mode_cool(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting the temperature in cool mode."""
    # Start with known initial conditions
    client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    client.read_hvac_mode.return_value = ("COOL", False)
    client.read_cooling_setpoint.return_value = 75
    await trigger_polling(menuai, freezer)
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.attributes["temperature"] == 75, state.attributes

    # Make the call, modifting the mock client to throw an exception on
    # read to ensure that the update is visible iff we call
    # async_update_ha_state.
    data = {ATTR_TEMPERATURE: 70}
    data[ATTR_ENTITY_ID] = "climate.system_1_zone_1"
    client.read_cooling_setpoint.side_effect = Exception("fake failure")
    await menuai.services.async_call(
        CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, data, blocking=True
    )

    # Verify effect.
    client.set_cooling_setpoint.assert_called_once_with(70)
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.attributes["temperature"] == 70


async def test_set_temperature_mode_heat(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting the temperature in heat mode."""

    # Start with known initial conditions
    client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    client.read_hvac_mode.return_value = ("HEAT", False)
    client.read_heating_setpoint.return_value = 60
    await trigger_polling(menuai, freezer)

    # Make the call, modifting the mock client to throw an exception on
    # read to ensure that the update is visible iff we call
    # async_update_ha_state.
    data = {"temperature": 65}
    data[ATTR_ENTITY_ID] = "climate.system_1_zone_1"
    client.read_heating_setpoint.side_effect = Exception("fake failure")
    await menuai.services.async_call(
        CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, data, blocking=True
    )
    # Verify effect.
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.attributes["temperature"] == 65, state.attributes


async def test_set_temperature_mode_heat_cool(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting the temperature in heat_cool mode."""

    # Enter heat_cool with known setpoints
    mock_client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    mock_client.read_hvac_mode.return_value = ("AUTO", False)
    mock_client.read_cooling_setpoint.return_value = 90
    mock_client.read_heating_setpoint.return_value = 40
    await trigger_polling(menuai, freezer)
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.state == "heat_cool"
    assert state.attributes["target_temp_low"] == 40
    assert state.attributes["target_temp_high"] == 90

    # Make the call, modifting the mock client to throw an exception on
    # read to ensure that the update is visible iff we call
    # async_update_ha_state.
    mock_client.read_heating_setpoint.side_effect = Exception("fake failure")
    mock_client.read_cooling_setpoint.side_effect = Exception("fake failure")
    data = {"target_temp_low": 70, "target_temp_high": 80}
    data[ATTR_ENTITY_ID] = "climate.system_1_zone_1"
    await menuai.services.async_call(
        CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, data, blocking=True
    )
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.attributes["target_temp_low"] == 70, state.attributes
    assert state.attributes["target_temp_high"] == 80, state.attributes
    mock_client.set_cooling_setpoint.assert_called_once_with(80)
    mock_client.set_heating_setpoint.assert_called_once_with(70)


async def test_set_fan_mode(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
) -> None:
    """Test that setting fan mode works."""
    mock_client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    fan_modes = ["auto", "low", "med", "high"]
    for mode in fan_modes:
        # Make the call, modifting the mock client to throw an exception on
        # read to ensure that the update is visible iff we call
        # async_update_ha_state.
        mock_client.read_fan_mode.side_effect = Exception("fake failure")
        data = {ATTR_FAN_MODE: mode}
        data[ATTR_ENTITY_ID] = "climate.system_1_zone_1"
        await menuai.services.async_call(
            CLIMATE_DOMAIN, SERVICE_SET_FAN_MODE, data, blocking=True
        )
        assert (
            menuai.states.get("climate.system_1_zone_1").attributes[ATTR_FAN_MODE] == mode
        )
        mock_client.set_fan_mode.assert_called_with(mode)


@pytest.mark.parametrize(
    ("hvac_mode", "evolution_mode"),
    [("heat_cool", "auto"), ("heat", "heat"), ("cool", "cool"), ("off", "off")],
)
async def test_set_hvac_mode(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    hvac_mode,
    evolution_mode,
) -> None:
    """Test that setting HVAC mode works."""
    mock_client = await mock_evolution_client_factory(1, 1, "/dev/unused")

    # Make the call, modifting the mock client to throw an exception on
    # read to ensure that the update is visible iff we call
    # async_update_ha_state.
    data = {ATTR_HVAC_MODE: hvac_mode}
    data[ATTR_ENTITY_ID] = "climate.system_1_zone_1"
    mock_client.read_hvac_mode.side_effect = Exception("fake failure")
    await menuai.services.async_call(
        CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, data, blocking=True
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("climate.system_1_zone_1").state == evolution_mode
    mock_client.set_hvac_mode.assert_called_with(evolution_mode)


@pytest.mark.parametrize(
    ("curr_temp", "expected_action"),
    [(62, HVACAction.HEATING), (70, HVACAction.OFF), (80, HVACAction.COOLING)],
)
async def test_read_hvac_action_heat_cool(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
    curr_temp: int,
    expected_action: HVACAction,
) -> None:
    """Test that we can read the current HVAC action in heat_cool mode."""
    htsp = 68
    clsp = 72

    mock_client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    mock_client.read_heating_setpoint.return_value = htsp
    mock_client.read_cooling_setpoint.return_value = clsp
    is_active = curr_temp < htsp or curr_temp > clsp
    mock_client.read_hvac_mode.return_value = ("auto", is_active)
    mock_client.read_current_temperature.return_value = curr_temp
    await trigger_polling(menuai, freezer)
    state = menuai.states.get("climate.system_1_zone_1")
    assert state.attributes[ATTR_HVAC_ACTION] == expected_action


@pytest.mark.parametrize(
    ("mode", "active", "expected_action"),
    [
        ("heat", True, "heating"),
        ("heat", False, "off"),
        ("cool", True, "cooling"),
        ("cool", False, "off"),
        ("off", False, "off"),
    ],
)
async def test_read_hvac_action(
    menuai: menuai,
    mock_evolution_entry: MockConfigEntry,
    mock_evolution_client_factory: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
    mode: str,
    active: bool,
    expected_action: str,
) -> None:
    """Test that we can read the current HVAC action."""
    # Initial state should be no action.
    assert (
        menuai.states.get("climate.system_1_zone_1").attributes[ATTR_HVAC_ACTION]
        == HVACAction.OFF
    )
    # Perturb the system and verify we see an action.
    mock_client = await mock_evolution_client_factory(1, 1, "/dev/unused")
    mock_client.read_heating_setpoint.return_value = 75  # Needed if mode == heat
    mock_client.read_hvac_mode.return_value = (mode, active)
    await trigger_polling(menuai, freezer)
    assert (
        menuai.states.get("climate.system_1_zone_1").attributes[ATTR_HVAC_ACTION]
        == expected_action
    )
