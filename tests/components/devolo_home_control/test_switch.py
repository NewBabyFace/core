"""Tests for the devolo Home Control switch platform."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .mocks import HomeControlMock, HomeControlMockSwitch


async def test_switch(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change of a switch device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSwitch()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SWITCH_DOMAIN}.test")
    assert state == snapshot
    assert entity_registry.async_get(f"{SWITCH_DOMAIN}.test") == snapshot

    # Emulate websocket message: switched on
    test_gateway.devices["Test"].binary_switch_property[
        "devolo.BinarySwitch:Test"
    ].state = True
    test_gateway.publisher.dispatch("Test", ("devolo.BinarySwitch:Test", True))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{SWITCH_DOMAIN}.test").state == STATE_ON

    with patch(
        "devolo_home_control_api.properties.binary_switch_property.BinarySwitchProperty.set"
    ) as set_value:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.test"},
            blocking=True,
        )  # In reality, this leads to a websocket message like already tested above
        set_value.assert_called_once_with(state=True)

        set_value.reset_mock()
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.test"},
            blocking=True,
        )  # In reality, this leads to a websocket message like already tested above
        set_value.assert_called_once_with(state=False)

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{SWITCH_DOMAIN}.test").state == STATE_UNAVAILABLE


async def test_remove_from_menuai(menuai: menuai) -> None:
    """Test removing entity."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSwitch()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SWITCH_DOMAIN}.test")
    assert state is not None
    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    assert test_gateway.publisher.unregister.call_count == 1
