"""Tests for the devolo Home Control climate."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import (
    ATTR_HVAC_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .mocks import HomeControlMock, HomeControlMockClimate


async def test_climate(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change of a climate device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockClimate()
    test_gateway.devices["Test"].value = 20
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{CLIMATE_DOMAIN}.test")
    assert state == snapshot
    assert entity_registry.async_get(f"{CLIMATE_DOMAIN}.test") == snapshot

    # Emulate websocket message: temperature changed
    test_gateway.publisher.dispatch("Test", ("Test", 21.0))
    await menuai.async_block_till_done()
    state = menuai.states.get(f"{CLIMATE_DOMAIN}.test")
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 21.0

    # Test setting temperature
    with patch(
        "devolo_home_control_api.properties.multi_level_switch_property.MultiLevelSwitchProperty.set"
    ) as set_value:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: f"{CLIMATE_DOMAIN}.test",
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 20.0,
            },
            blocking=True,
        )  # In reality, this leads to a websocket message like already tested above
        set_value.assert_called_once_with(20.0)

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{CLIMATE_DOMAIN}.test").state == STATE_UNAVAILABLE


async def test_remove_from_menuai(menuai: menuai) -> None:
    """Test removing entity."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockClimate()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{CLIMATE_DOMAIN}.test")
    assert state is not None
    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    assert test_gateway.publisher.unregister.call_count == 2
