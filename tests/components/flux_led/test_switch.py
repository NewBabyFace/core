"""Tests for switch platform."""

from flux_led.const import MODE_MUSIC

from menuai.components import flux_led
from menuai.components.flux_led.const import (
    CONF_REMOTE_ACCESS_ENABLED,
    CONF_REMOTE_ACCESS_HOST,
    CONF_REMOTE_ACCESS_PORT,
    DOMAIN,
)
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from . import (
    DEFAULT_ENTRY_TITLE,
    IP_ADDRESS,
    MAC_ADDRESS,
    _mocked_bulb,
    _mocked_switch,
    _patch_discovery,
    _patch_wifibulb,
    async_mock_device_turn_off,
    async_mock_device_turn_on,
)

from tests.common import MockConfigEntry


async def test_switch_on_off(menuai: menuai) -> None:
    """Test a smart plug."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    switch = _mocked_switch()
    with _patch_discovery(), _patch_wifibulb(device=switch):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "switch.bulb_rgbcw_ddeeff"

    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.async_turn_off.assert_called_once()

    await async_mock_device_turn_off(menuai, switch)
    assert menuai.states.get(entity_id).state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.async_turn_on.assert_called_once()
    switch.async_turn_on.reset_mock()

    await async_mock_device_turn_on(menuai, switch)
    assert menuai.states.get(entity_id).state == STATE_ON


async def test_remote_access_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a remote access switch unique id."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_REMOTE_ACCESS_HOST: "any",
            CONF_REMOTE_ACCESS_ENABLED: True,
            CONF_REMOTE_ACCESS_PORT: 1234,
            CONF_HOST: IP_ADDRESS,
            CONF_NAME: DEFAULT_ENTRY_TITLE,
        },
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "switch.bulb_rgbcw_ddeeff_remote_access"
    assert (
        entity_registry.async_get(entity_id).unique_id == f"{MAC_ADDRESS}_remote_access"
    )


async def test_effects_speed_unique_id_no_discovery(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a remote access switch unique id when discovery fails."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_REMOTE_ACCESS_HOST: "any",
            CONF_REMOTE_ACCESS_ENABLED: True,
            CONF_REMOTE_ACCESS_PORT: 1234,
            CONF_HOST: IP_ADDRESS,
            CONF_NAME: DEFAULT_ENTRY_TITLE,
        },
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(no_device=True), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "switch.bulb_rgbcw_ddeeff_remote_access"
    assert (
        entity_registry.async_get(entity_id).unique_id
        == f"{config_entry.entry_id}_remote_access"
    )


async def test_remote_access_on_off(menuai: menuai) -> None:
    """Test enable/disable remote access."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_REMOTE_ACCESS_HOST: "any",
            CONF_REMOTE_ACCESS_ENABLED: True,
            CONF_REMOTE_ACCESS_PORT: 1234,
            CONF_HOST: IP_ADDRESS,
            CONF_NAME: DEFAULT_ENTRY_TITLE,
        },
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(), _patch_wifibulb(bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "switch.bulb_rgbcw_ddeeff_remote_access"

    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_disable_remote_access.assert_called_once()
    assert menuai.states.get(entity_id).state == STATE_OFF
    assert config_entry.data[CONF_REMOTE_ACCESS_ENABLED] is False

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_enable_remote_access.assert_called_once()

    assert menuai.states.get(entity_id).state == STATE_ON
    assert config_entry.data[CONF_REMOTE_ACCESS_ENABLED] is True


async def test_music_mode_switch(menuai: menuai) -> None:
    """Test music mode switch."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.raw_state = bulb.raw_state._replace(model_num=0xA3)  # has music mode
    bulb.microphone = True
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "switch.bulb_rgbcw_ddeeff_music"

    assert menuai.states.get(entity_id).state == STATE_OFF

    bulb.effect = MODE_MUSIC
    bulb.is_on = False
    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_set_music_mode.assert_called_once()
    assert menuai.states.get(entity_id).state == STATE_OFF

    bulb.async_set_music_mode.reset_mock()
    bulb.is_on = True
    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_set_music_mode.assert_called_once()
    assert menuai.states.get(entity_id).state == STATE_ON

    bulb.effect = None
    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_set_levels.assert_called_once()
    assert menuai.states.get(entity_id).state == STATE_OFF
