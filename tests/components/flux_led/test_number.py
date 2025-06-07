"""Tests for the flux_led number platform."""

from datetime import timedelta

from flux_led.const import COLOR_MODE_RGB as FLUX_COLOR_MODE_RGB
import pytest

from menuai.components import flux_led
from menuai.components.flux_led import number as flux_number
from menuai.components.flux_led.const import DOMAIN
from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import (
    DEFAULT_ENTRY_TITLE,
    IP_ADDRESS,
    MAC_ADDRESS,
    _mocked_bulb,
    _patch_discovery,
    _patch_wifibulb,
    async_mock_device_turn_off,
    async_mock_device_turn_on,
    async_mock_effect_speed,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_effects_speed_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a number unique id."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "number.bulb_rgbcw_ddeeff_effect_speed"
    assert entity_registry.async_get(entity_id).unique_id == MAC_ADDRESS


async def test_effects_speed_unique_id_no_discovery(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a number unique id."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(no_device=True), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "number.bulb_rgbcw_ddeeff_effect_speed"
    assert entity_registry.async_get(entity_id).unique_id == config_entry.entry_id


async def test_rgb_light_effect_speed(menuai: menuai) -> None:
    """Test an rgb light with an effect."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.raw_state = bulb.raw_state._replace(model_num=0x33)  # RGB only model

    bulb.color_modes = {FLUX_COLOR_MODE_RGB}
    bulb.color_mode = FLUX_COLOR_MODE_RGB

    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    await async_mock_device_turn_on(menuai, bulb)

    light_entity_id = "light.bulb_rgbcw_ddeeff"
    number_entity_id = "number.bulb_rgbcw_ddeeff_effect_speed"
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
            blocking=True,
        )

    state = menuai.states.get(light_entity_id)
    assert state.state == STATE_ON

    bulb.effect = "colorloop"
    bulb.speed = 50
    await async_mock_device_turn_off(menuai, bulb)
    state = menuai.states.get(number_entity_id)
    assert state.state == "50"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    bulb.async_set_effect.assert_called_with("colorloop", 100, 50)
    bulb.async_set_effect.reset_mock()

    await async_mock_effect_speed(menuai, bulb, "red_fade", 50)
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 50},
        blocking=True,
    )
    bulb.async_set_effect.assert_called_with("red_fade", 50, 50)
    bulb.async_set_effect.reset_mock()

    state = menuai.states.get(number_entity_id)
    assert state.state == "50"


async def test_original_addressable_light_effect_speed(menuai: menuai) -> None:
    """Test an original addressable light with an effect."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.speed_adjust_off = False
    bulb.raw_state = bulb.raw_state._replace(
        model_num=0xA1
    )  # Original addressable model
    bulb.color_modes = {FLUX_COLOR_MODE_RGB}
    bulb.color_mode = FLUX_COLOR_MODE_RGB
    bulb.effect = "7 colors change gradually"
    bulb.speed = 50
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    await async_mock_device_turn_on(menuai, bulb)

    light_entity_id = "light.bulb_rgbcw_ddeeff"
    number_entity_id = "number.bulb_rgbcw_ddeeff_effect_speed"

    state = menuai.states.get(light_entity_id)
    assert state.state == STATE_ON

    state = menuai.states.get(number_entity_id)
    assert state.state == "50"

    await async_mock_device_turn_off(menuai, bulb)

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
            blocking=True,
        )

    await async_mock_device_turn_on(menuai, bulb)
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    bulb.async_set_effect.assert_called_with("7 colors change gradually", 100, 50)
    bulb.async_set_effect.reset_mock()
    await async_mock_effect_speed(menuai, bulb, "7 colors run in olivary", 100)

    state = menuai.states.get(number_entity_id)
    assert state.state == "100"


async def test_addressable_light_effect_speed(menuai: menuai) -> None:
    """Test an addressable light with an effect."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.addressable = True
    bulb.raw_state = bulb.raw_state._replace(
        model_num=0xA2
    )  # Original addressable model
    bulb.color_modes = {FLUX_COLOR_MODE_RGB}
    bulb.color_mode = FLUX_COLOR_MODE_RGB
    bulb.effect = "RBM 1"
    bulb.speed = 50
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    await async_mock_device_turn_on(menuai, bulb)

    light_entity_id = "light.bulb_rgbcw_ddeeff"
    number_entity_id = "number.bulb_rgbcw_ddeeff_effect_speed"

    state = menuai.states.get(light_entity_id)
    assert state.state == STATE_ON

    state = menuai.states.get(number_entity_id)
    assert state.state == "50"

    await async_mock_device_turn_off(menuai, bulb)

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    bulb.async_set_effect.assert_called_with("RBM 1", 100, 50)
    bulb.async_set_effect.reset_mock()

    await async_mock_device_turn_on(menuai, bulb)
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    bulb.async_set_effect.assert_called_with("RBM 1", 100, 50)
    bulb.async_set_effect.reset_mock()
    await async_mock_effect_speed(menuai, bulb, "RBM 2", 100)

    state = menuai.states.get(number_entity_id)
    assert state.state == "100"


async def test_addressable_light_pixel_config(menuai: menuai) -> None:
    """Test an addressable light pixel config."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.raw_state = bulb.raw_state._replace(
        model_num=0xA2
    )  # Original addressable model
    bulb.color_modes = {FLUX_COLOR_MODE_RGB}
    bulb.color_mode = FLUX_COLOR_MODE_RGB
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    pixels_per_segment_entity_id = "number.bulb_rgbcw_ddeeff_pixels_per_segment"
    state = menuai.states.get(pixels_per_segment_entity_id)
    assert state.state == "300"

    segments_entity_id = "number.bulb_rgbcw_ddeeff_segments"
    state = menuai.states.get(segments_entity_id)
    assert state.state == "2"

    music_pixels_per_segment_entity_id = (
        "number.bulb_rgbcw_ddeeff_music_pixels_per_segment"
    )
    state = menuai.states.get(music_pixels_per_segment_entity_id)
    assert state.state == "150"

    music_segments_entity_id = "number.bulb_rgbcw_ddeeff_music_segments"
    state = menuai.states.get(music_segments_entity_id)
    assert state.state == "4"
    await menuai.async_block_till_done(wait_background_tasks=True)

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: pixels_per_segment_entity_id, ATTR_VALUE: 5000},
            blocking=True,
        )

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: pixels_per_segment_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    async_fire_time_changed(
        menuai, dt_util.utcnow() + timedelta(seconds=flux_number.DEBOUNCE_TIME)
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    bulb.async_set_device_config.assert_called_with(pixels_per_segment=100)
    bulb.async_set_device_config.reset_mock()

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: music_pixels_per_segment_entity_id, ATTR_VALUE: 5000},
            blocking=True,
        )

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: music_pixels_per_segment_entity_id, ATTR_VALUE: 100},
        blocking=True,
    )
    async_fire_time_changed(
        menuai, dt_util.utcnow() + timedelta(seconds=flux_number.DEBOUNCE_TIME)
    )
    await menuai.async_block_till_done(wait_background_tasks=True)
    bulb.async_set_device_config.assert_called_with(music_pixels_per_segment=100)
    bulb.async_set_device_config.reset_mock()

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: segments_entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: segments_entity_id, ATTR_VALUE: 5},
        blocking=True,
    )
    async_fire_time_changed(
        menuai, dt_util.utcnow() + timedelta(seconds=flux_number.DEBOUNCE_TIME)
    )
    await menuai.async_block_till_done(wait_background_tasks=True)
    bulb.async_set_device_config.assert_called_with(segments=5)
    bulb.async_set_device_config.reset_mock()

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: music_segments_entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: music_segments_entity_id, ATTR_VALUE: 5},
        blocking=True,
    )
    async_fire_time_changed(
        menuai, dt_util.utcnow() + timedelta(seconds=flux_number.DEBOUNCE_TIME)
    )
    await menuai.async_block_till_done(wait_background_tasks=True)
    bulb.async_set_device_config.assert_called_with(music_segments=5)
    bulb.async_set_device_config.reset_mock()


async def test_addressable_light_pixel_config_music_disabled(
    menuai: menuai,
) -> None:
    """Test an addressable light pixel config with music pixels disabled."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NAME: DEFAULT_ENTRY_TITLE},
        unique_id=MAC_ADDRESS,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    bulb.pixels_per_segment = 150
    bulb.segments = 1
    bulb.music_pixels_per_segment = 150
    bulb.music_segments = 1
    bulb.raw_state = bulb.raw_state._replace(
        model_num=0xA2
    )  # Original addressable model
    bulb.color_modes = {FLUX_COLOR_MODE_RGB}
    bulb.color_mode = FLUX_COLOR_MODE_RGB
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, flux_led.DOMAIN, {flux_led.DOMAIN: {}})
        await menuai.async_block_till_done()

    pixels_per_segment_entity_id = "number.bulb_rgbcw_ddeeff_pixels_per_segment"
    state = menuai.states.get(pixels_per_segment_entity_id)
    assert state.state == "150"

    segments_entity_id = "number.bulb_rgbcw_ddeeff_segments"
    state = menuai.states.get(segments_entity_id)
    assert state.state == "1"

    music_pixels_per_segment_entity_id = (
        "number.bulb_rgbcw_ddeeff_music_pixels_per_segment"
    )
    state = menuai.states.get(music_pixels_per_segment_entity_id)
    assert state.state == STATE_UNAVAILABLE

    music_segments_entity_id = "number.bulb_rgbcw_ddeeff_music_segments"
    state = menuai.states.get(music_segments_entity_id)
    assert state.state == STATE_UNAVAILABLE
