"""The tests for the demo water_heater component."""

from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components import water_heater
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from tests.components.water_heater import common

ENTITY_WATER_HEATER = "water_heater.demo_water_heater"
ENTITY_WATER_HEATER_CELSIUS = "water_heater.demo_water_heater_celsius"


@pytest.fixture
async def water_heater_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.WATER_HEATER],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, water_heater_only: None):
    """Set up demo component."""
    menuai.config.units = US_CUSTOMARY_SYSTEM
    assert await async_setup_component(
        menuai, water_heater.DOMAIN, {"water_heater": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


async def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 119
    assert state.attributes.get("away_mode") == "off"
    assert state.attributes.get("operation_mode") == "eco"
    assert state.attributes.get("target_temp_step") == 1


async def test_default_setup_params(menuai: menuai) -> None:
    """Test the setup with default parameters."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("min_temp") == 110
    assert state.attributes.get("max_temp") == 140


async def test_set_only_target_temp_bad_attr(menuai: menuai) -> None:
    """Test setting the target temperature without required attribute."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 119
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(menuai, None, ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 119


async def test_set_only_target_temp(menuai: menuai) -> None:
    """Test the setting of the target temperature."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 119
    await common.async_set_temperature(menuai, 110, ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 110


async def test_set_operation_bad_attr_and_state(menuai: menuai) -> None:
    """Test setting operation mode without required attribute.

    Also check the state.
    """
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "eco"
    assert state.state == "eco"
    with pytest.raises(vol.Invalid):
        await common.async_set_operation_mode(menuai, None, ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "eco"
    assert state.state == "eco"


async def test_set_operation(menuai: menuai) -> None:
    """Test setting of new operation mode."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "eco"
    assert state.state == "eco"
    await common.async_set_operation_mode(menuai, "electric", ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "electric"
    assert state.state == "electric"


async def test_set_away_mode_bad_attr(menuai: menuai) -> None:
    """Test setting the away mode without required attribute."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("away_mode") == "off"
    with pytest.raises(vol.Invalid):
        await common.async_set_away_mode(menuai, None, ENTITY_WATER_HEATER)
    assert state.attributes.get("away_mode") == "off"


async def test_set_away_mode_on(menuai: menuai) -> None:
    """Test setting the away mode on/true."""
    await common.async_set_away_mode(menuai, True, ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("away_mode") == "on"


async def test_set_away_mode_off(menuai: menuai) -> None:
    """Test setting the away mode off/false."""
    await common.async_set_away_mode(menuai, False, ENTITY_WATER_HEATER_CELSIUS)
    state = menuai.states.get(ENTITY_WATER_HEATER_CELSIUS)
    assert state.attributes.get("away_mode") == "off"


async def test_set_only_target_temp_with_convert(menuai: menuai) -> None:
    """Test the setting of the target temperature."""
    state = menuai.states.get(ENTITY_WATER_HEATER_CELSIUS)
    assert state.attributes.get("temperature") == 113
    await common.async_set_temperature(menuai, 114, ENTITY_WATER_HEATER_CELSIUS)
    state = menuai.states.get(ENTITY_WATER_HEATER_CELSIUS)
    assert state.attributes.get("temperature") == 114


async def test_turn_on_off(menuai: menuai) -> None:
    """Test turn on and off."""
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("temperature") == 119
    assert state.attributes.get("away_mode") == "off"
    assert state.attributes.get("operation_mode") == "eco"

    await common.async_turn_off(menuai, ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "off"

    await common.async_turn_on(menuai, ENTITY_WATER_HEATER)
    state = menuai.states.get(ENTITY_WATER_HEATER)
    assert state.attributes.get("operation_mode") == "eco"
