"""Tests for button platform."""

from menuai.components import flux_led
from menuai.components.button import DOMAIN as BUTTON_DOMAIN
from menuai.components.flux_led.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID, CONF_HOST, CONF_NAME
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import (
    DEFAULT_ENTRY_TITLE,
    FLUX_DISCOVERY,
    IP_ADDRESS,
    MAC_ADDRESS,
    _mock_config_entry_for_bulb,
    _mocked_bulb,
    _mocked_switch,
    _patch_discovery,
    _patch_wifibulb,
)

from tests.common import MockConfigEntry


async def test_button_reboot(menuai: menuai) -> None:
    """Test a smart plug can be rebooted."""
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

    entity_id = "button.bulb_rgbcw_ddeeff_restart"

    assert menuai.states.get(entity_id)

    await menuai.services.async_call(
        BUTTON_DOMAIN, "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.async_reboot.assert_called_once()


async def test_button_unpair_remotes_bulb(menuai: menuai) -> None:
    """Test that remotes can be unpaired from a bulb."""
    _mock_config_entry_for_bulb(menuai)
    bulb = _mocked_bulb()
    bulb.discovery = FLUX_DISCOVERY
    with _patch_discovery(device=FLUX_DISCOVERY), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "button.bulb_rgbcw_ddeeff_unpair_remotes"
    assert menuai.states.get(entity_id)

    await menuai.services.async_call(
        BUTTON_DOMAIN, "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.async_unpair_remotes.assert_called_once()


async def test_button_unpair_remotes_smart_switch(menuai: menuai) -> None:
    """Test that remotes can be unpaired from a smart switch."""
    _mock_config_entry_for_bulb(menuai)
    switch = _mocked_switch()
    switch.discovery = FLUX_DISCOVERY
    with _patch_discovery(device=FLUX_DISCOVERY), _patch_wifibulb(device=switch):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "button.bulb_rgbcw_ddeeff_unpair_remotes"
    assert menuai.states.get(entity_id)

    await menuai.services.async_call(
        BUTTON_DOMAIN, "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.async_unpair_remotes.assert_called_once()
