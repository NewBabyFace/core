"""Tests for gree component."""

from unittest.mock import patch

from greeclimate.exceptions import DeviceTimeoutError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.gree.const import DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

ENTITY_ID_PANEL_LIGHT = f"{SWITCH_DOMAIN}.fake_device_1_panel_light"
ENTITY_ID_HEALTH_MODE = f"{SWITCH_DOMAIN}.fake_device_1_health_mode"
ENTITY_ID_QUIET_MODE = f"{SWITCH_DOMAIN}.fake_device_1_quiet_mode"
ENTITY_ID_FRESH_AIR = f"{SWITCH_DOMAIN}.fake_device_1_fresh_air"
ENTITY_ID_XTRA_FAN = f"{SWITCH_DOMAIN}.fake_device_1_xtra_fan"


async def async_setup_gree(menuai: menuai) -> MockConfigEntry:
    """Set up the gree switch platform."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {SWITCH_DOMAIN: {}}})
    await menuai.async_block_till_done()
    return entry


@patch("menuai.components.gree.PLATFORMS", [SWITCH_DOMAIN])
async def test_registry_settings(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for entity registry settings (disabled_by, unique_id)."""
    entry = await async_setup_gree(menuai)

    state = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert state == snapshot


@pytest.mark.parametrize(
    "entity",
    [
        ENTITY_ID_PANEL_LIGHT,
        ENTITY_ID_HEALTH_MODE,
        ENTITY_ID_QUIET_MODE,
        ENTITY_ID_FRESH_AIR,
        ENTITY_ID_XTRA_FAN,
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_send_switch_on(menuai: menuai, entity: str) -> None:
    """Test for sending power on command to the device."""
    await async_setup_gree(menuai)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    "entity",
    [
        ENTITY_ID_PANEL_LIGHT,
        ENTITY_ID_HEALTH_MODE,
        ENTITY_ID_QUIET_MODE,
        ENTITY_ID_FRESH_AIR,
        ENTITY_ID_XTRA_FAN,
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_send_switch_on_device_timeout(
    menuai: menuai, device, entity: str
) -> None:
    """Test for sending power on command to the device with a device timeout."""
    device().push_state_update.side_effect = DeviceTimeoutError

    await async_setup_gree(menuai)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    "entity",
    [
        ENTITY_ID_PANEL_LIGHT,
        ENTITY_ID_HEALTH_MODE,
        ENTITY_ID_QUIET_MODE,
        ENTITY_ID_FRESH_AIR,
        ENTITY_ID_XTRA_FAN,
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_send_switch_off(menuai: menuai, entity: str) -> None:
    """Test for sending power on command to the device."""
    await async_setup_gree(menuai)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    "entity",
    [
        ENTITY_ID_PANEL_LIGHT,
        ENTITY_ID_HEALTH_MODE,
        ENTITY_ID_QUIET_MODE,
        ENTITY_ID_FRESH_AIR,
        ENTITY_ID_XTRA_FAN,
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_send_switch_toggle(menuai: menuai, entity: str) -> None:
    """Test for sending power on command to the device."""
    await async_setup_gree(menuai)

    # Turn the service on first
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_ON

    # Toggle it off
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_OFF

    # Toggle is back on
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: entity},
        blocking=True,
    )

    state = menuai.states.get(entity)
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entity_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for entity registry settings (disabled_by, unique_id)."""
    await async_setup_gree(menuai)

    state = menuai.states.async_all(SWITCH_DOMAIN)
    assert state == snapshot
