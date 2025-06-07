"""Tests for the devolo Home Control binary sensors."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.siren import DOMAIN as SIREN_DOMAIN
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .mocks import HomeControlMock, HomeControlMockSiren


@pytest.mark.usefixtures("mock_zeroconf")
async def test_siren(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change of a siren device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSiren()
    test_gateway.devices["Test"].status = 0
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SIREN_DOMAIN}.test")
    assert state == snapshot
    assert entity_registry.async_get(f"{SIREN_DOMAIN}.test") == snapshot

    # Emulate websocket message: sensor turned on
    test_gateway.publisher.dispatch("Test", ("devolo.SirenMultiLevelSwitch:Test", 1))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{SIREN_DOMAIN}.test").state == STATE_ON

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{SIREN_DOMAIN}.test").state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("mock_zeroconf")
async def test_siren_switching(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test setup and state change via switching of a siren device."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSiren()
    test_gateway.devices["Test"].status = 0
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SIREN_DOMAIN}.test")
    assert state == snapshot
    assert entity_registry.async_get(f"{SIREN_DOMAIN}.test") == snapshot

    with patch(
        "devolo_home_control_api.properties.multi_level_switch_property.MultiLevelSwitchProperty.set"
    ) as property_set:
        await menuai.services.async_call(
            "siren",
            "turn_on",
            {"entity_id": f"{SIREN_DOMAIN}.test"},
            blocking=True,
        )
        # The real device state is changed by a websocket message
        test_gateway.publisher.dispatch(
            "Test", ("devolo.SirenMultiLevelSwitch:Test", 1)
        )
        await menuai.async_block_till_done()
        property_set.assert_called_once_with(1)

    with patch(
        "devolo_home_control_api.properties.multi_level_switch_property.MultiLevelSwitchProperty.set"
    ) as property_set:
        await menuai.services.async_call(
            "siren",
            "turn_off",
            {"entity_id": f"{SIREN_DOMAIN}.test"},
            blocking=True,
        )
        # The real device state is changed by a websocket message
        test_gateway.publisher.dispatch(
            "Test", ("devolo.SirenMultiLevelSwitch:Test", 0)
        )
        await menuai.async_block_till_done()
        assert menuai.states.get(f"{SIREN_DOMAIN}.test").state == STATE_OFF
        property_set.assert_called_once_with(0)


@pytest.mark.usefixtures("mock_zeroconf")
async def test_siren_change_default_tone(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test changing the default tone on message."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSiren()
    test_gateway.devices["Test"].status = 0
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SIREN_DOMAIN}.test")
    assert state == snapshot
    assert entity_registry.async_get(f"{SIREN_DOMAIN}.test") == snapshot

    with patch(
        "devolo_home_control_api.properties.multi_level_switch_property.MultiLevelSwitchProperty.set"
    ) as property_set:
        test_gateway.publisher.dispatch("Test", ("mss:Test", 2))
        await menuai.services.async_call(
            "siren",
            "turn_on",
            {"entity_id": f"{SIREN_DOMAIN}.test"},
            blocking=True,
        )
        property_set.assert_called_once_with(2)


@pytest.mark.usefixtures("mock_zeroconf")
async def test_remove_from_menuai(menuai: menuai) -> None:
    """Test removing entity."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockSiren()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get(f"{SIREN_DOMAIN}.test")
    assert state is not None
    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    test_gateway.publisher.unregister.assert_called_once()
