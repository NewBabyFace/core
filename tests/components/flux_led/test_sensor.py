"""Tests for flux_led sensor platform."""

from menuai.components import flux_led
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import (
    FLUX_DISCOVERY,
    _mock_config_entry_for_bulb,
    _mocked_bulb,
    _patch_discovery,
    _patch_wifibulb,
)


async def test_paired_remotes_sensor(menuai: menuai) -> None:
    """Test that the paired remotes sensor has the correct value."""
    _mock_config_entry_for_bulb(menuai)
    bulb = _mocked_bulb()
    bulb.discovery = FLUX_DISCOVERY
    with _patch_discovery(device=FLUX_DISCOVERY), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "sensor.bulb_rgbcw_ddeeff_paired_remotes"
    assert menuai.states.get(entity_id).state == "2"
