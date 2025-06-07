"""Tests for the Freebox init."""

from unittest.mock import ANY, Mock

from pytest_unordered import unordered

from menuai.components.device_tracker import DOMAIN as DT_DOMAIN
from menuai.components.freebox.const import DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import MOCK_HOST, MOCK_PORT

from tests.common import MockConfigEntry


async def test_setup(menuai: menuai, router: Mock) -> None:
    """Test setup of integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        unique_id=MOCK_HOST,
    )
    entry.add_to_menuai(menuai)
    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
    assert menuai.config_entries.async_entries() == unordered([entry, ANY])

    assert router.call_count == 1
    assert router().open.call_count == 1


async def test_setup_import(menuai: menuai, router: Mock) -> None:
    """Test setup of integration from import."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        unique_id=MOCK_HOST,
    )
    entry.add_to_menuai(menuai)
    assert await async_setup_component(
        menuai, DOMAIN, {DOMAIN: {CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT}}
    )
    await menuai.async_block_till_done()
    assert menuai.config_entries.async_entries() == unordered([entry, ANY])

    assert router.call_count == 1
    assert router().open.call_count == 1


async def test_unload_remove(menuai: menuai, router: Mock) -> None:
    """Test unload and remove of integration."""
    entity_id_dt = f"{DT_DOMAIN}.freebox_server_r2"
    entity_id_sensor = f"{SENSOR_DOMAIN}.freebox_download_speed"
    entity_id_switch = f"{SWITCH_DOMAIN}.freebox_wifi"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
    )
    entry.add_to_menuai(menuai)

    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert entry is config_entries[0]

    assert await async_setup_component(menuai, DOMAIN, {}) is True
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    state_dt = menuai.states.get(entity_id_dt)
    assert state_dt
    state_sensor = menuai.states.get(entity_id_sensor)
    assert state_sensor
    state_switch = menuai.states.get(entity_id_switch)
    assert state_switch

    await menuai.config_entries.async_unload(entry.entry_id)

    assert entry.state is ConfigEntryState.NOT_LOADED
    state_dt = menuai.states.get(entity_id_dt)
    assert state_dt.state == STATE_UNAVAILABLE
    state_sensor = menuai.states.get(entity_id_sensor)
    assert state_sensor.state == STATE_UNAVAILABLE
    state_switch = menuai.states.get(entity_id_switch)
    assert state_switch.state == STATE_UNAVAILABLE

    assert router().close.call_count == 1

    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert router().close.call_count == 1
    assert entry.state is ConfigEntryState.NOT_LOADED
    state_dt = menuai.states.get(entity_id_dt)
    assert state_dt is None
    state_sensor = menuai.states.get(entity_id_sensor)
    assert state_sensor is None
    state_switch = menuai.states.get(entity_id_switch)
    assert state_switch is None
