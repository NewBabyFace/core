"""Tests for the lifx integration select entity."""

from datetime import timedelta

import pytest

from menuai.components import lifx
from menuai.components.lifx.const import DOMAIN
from menuai.components.select import DOMAIN as SELECT_DOMAIN
from menuai.const import ATTR_ENTITY_ID, CONF_HOST, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import (
    DEFAULT_ENTRY_TITLE,
    IP_ADDRESS,
    SERIAL,
    MockLifxCommand,
    _mocked_infrared_bulb,
    _mocked_light_strip,
    _patch_config_flow_try_connect,
    _patch_device,
    _patch_discovery,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_theme_select(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test selecting a theme."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_light_strip()
    bulb.product = 38
    bulb.power_level = 0
    bulb.color = [0, 0, 65535, 3500]
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_theme"

    entity = entity_registry.async_get(entity_id)
    assert entity
    assert not entity.disabled

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {ATTR_ENTITY_ID: entity_id, "option": "intense"},
        blocking=True,
    )

    assert len(bulb.set_extended_color_zones.calls) == 1
    bulb.set_extended_color_zones.reset_mock()


async def test_infrared_brightness(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    unique_id = f"{SERIAL}_infrared_brightness"
    entity_id = "select.my_bulb_infrared_brightness"

    entity = entity_registry.async_get(entity_id)
    assert entity
    assert not entity.disabled
    assert entity.unique_id == unique_id

    state = menuai.states.get(entity_id)
    assert state.state == "100%"


@pytest.mark.usefixtures("mock_discovery")
async def test_set_infrared_brightness_25_percent(menuai: menuai) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_infrared_brightness"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {ATTR_ENTITY_ID: entity_id, "option": "25%"},
        blocking=True,
    )

    bulb.get_infrared = MockLifxCommand(bulb, infrared_brightness=16383)

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert bulb.set_infrared.calls[0][0][0] == 16383

    state = menuai.states.get(entity_id)
    assert state.state == "25%"

    bulb.set_infrared.reset_mock()


@pytest.mark.usefixtures("mock_discovery")
async def test_set_infrared_brightness_50_percent(menuai: menuai) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_infrared_brightness"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {ATTR_ENTITY_ID: entity_id, "option": "50%"},
        blocking=True,
    )

    bulb.get_infrared = MockLifxCommand(bulb, infrared_brightness=32767)

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert bulb.set_infrared.calls[0][0][0] == 32767

    state = menuai.states.get(entity_id)
    assert state.state == "50%"

    bulb.set_infrared.reset_mock()


@pytest.mark.usefixtures("mock_discovery")
async def test_set_infrared_brightness_100_percent(menuai: menuai) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_infrared_brightness"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {ATTR_ENTITY_ID: entity_id, "option": "100%"},
        blocking=True,
    )

    bulb.get_infrared = MockLifxCommand(bulb, infrared_brightness=65535)

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert bulb.set_infrared.calls[0][0][0] == 65535

    state = menuai.states.get(entity_id)
    assert state.state == "100%"

    bulb.set_infrared.reset_mock()


@pytest.mark.usefixtures("mock_discovery")
async def test_disable_infrared(menuai: menuai) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_infrared_brightness"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {ATTR_ENTITY_ID: entity_id, "option": "Disabled"},
        blocking=True,
    )

    bulb.get_infrared = MockLifxCommand(bulb, infrared_brightness=0)

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert bulb.set_infrared.calls[0][0][0] == 0

    state = menuai.states.get(entity_id)
    assert state.state == "Disabled"

    bulb.set_infrared.reset_mock()


@pytest.mark.usefixtures("mock_discovery")
async def test_invalid_infrared_brightness(menuai: menuai) -> None:
    """Test getting and setting infrared brightness."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_infrared_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "select.my_bulb_infrared_brightness"

    bulb.get_infrared = MockLifxCommand(bulb, infrared_brightness=12345)

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNKNOWN
