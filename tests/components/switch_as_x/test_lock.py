"""Tests for the Switch as X Lock platform."""

from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockState
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.components.switch_as_x.config_flow import SwitchAsXConfigFlowHandler
from menuai.components.switch_as_x.const import (
    CONF_INVERT,
    CONF_TARGET_DOMAIN,
    DOMAIN,
)
from menuai.const import (
    CONF_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_UNLOCK,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_default_state(menuai: menuai) -> None:
    """Test lock switch default state."""
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.test",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: Platform.LOCK,
        },
        title="candy_jar",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.candy_jar")
    assert state is not None
    assert state.state == "unavailable"


async def test_service_calls(menuai: menuai) -> None:
    """Test service calls affecting the switch as lock entity."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: Platform.LOCK,
        },
        title="Title is ignored",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {CONF_ENTITY_ID: "lock.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {CONF_ENTITY_ID: "lock.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED


async def test_service_calls_inverted(menuai: menuai) -> None:
    """Test service calls affecting the switch as lock entity."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: True,
            CONF_TARGET_DOMAIN: Platform.LOCK,
        },
        title="Title is ignored",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {CONF_ENTITY_ID: "lock.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {CONF_ENTITY_ID: "lock.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("lock.decorative_lights").state == LockState.LOCKED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("lock.decorative_lights").state == LockState.UNLOCKED
