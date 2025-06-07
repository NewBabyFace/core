"""Tests for the devolo Home Control binary sensors."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .mocks import (
    HomeControlMock,
    HomeControlMockBinarySensor,
    HomeControlMockDisabledBinarySensor,
    HomeControlMockRemoteControl,
)


@pytest.mark.usefixtures("mock_zeroconf")
async def test_binary_sensor(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change of a binary sensor device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockBinarySensor()
    test_gateway.devices["Test"].status = 0
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_door")
    assert state == snapshot
    assert entity_registry.async_get(f"{BINARY_SENSOR_DOMAIN}.test_door") == snapshot

    state = menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_overload")
    assert state == snapshot
    assert (
        entity_registry.async_get(f"{BINARY_SENSOR_DOMAIN}.test_overload") == snapshot
    )

    # Emulate websocket message: sensor turned on
    test_gateway.publisher.dispatch("Test", ("Test", True))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_door").state == STATE_ON

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_door").state == STATE_UNAVAILABLE
    )


@pytest.mark.usefixtures("mock_zeroconf")
async def test_remote_control(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change of a remote control device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockRemoteControl()
    test_gateway.devices["Test"].status = 0
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_button_1")
    assert state == snapshot
    assert (
        entity_registry.async_get(f"{BINARY_SENSOR_DOMAIN}.test_button_1") == snapshot
    )

    # Emulate websocket message: button pressed
    test_gateway.publisher.dispatch("Test", ("Test", 1))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_button_1").state == STATE_ON

    # Emulate websocket message: button released
    test_gateway.publisher.dispatch("Test", ("Test", 0))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_button_1").state == STATE_OFF

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_button_1").state
        == STATE_UNAVAILABLE
    )


@pytest.mark.usefixtures("mock_zeroconf")
async def test_disabled(menuai: menuai) -> None:
    """Test setup of a disabled device."""
    entry = configure_integration(menuai)
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[HomeControlMockDisabledBinarySensor(), HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_door") is None


@pytest.mark.usefixtures("mock_zeroconf")
async def test_remove_from_menuai(menuai: menuai) -> None:
    """Test removing entity."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockBinarySensor()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test_door")
    assert state is not None
    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    assert test_gateway.publisher.unregister.call_count == 2
