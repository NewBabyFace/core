"""Tests for WiZ binary_sensor platform."""

from menuai.components import wiz
from menuai.components.wiz.binary_sensor import OCCUPANCY_UNIQUE_ID
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, STATE_OFF, STATE_ON, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from . import (
    FAKE_IP,
    FAKE_MAC,
    _mocked_wizlight,
    _patch_discovery,
    _patch_wizlight,
    async_push_update,
    async_setup_integration,
)

from tests.common import MockConfigEntry


async def test_binary_sensor_created_from_push_updates(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a binary sensor created from push updates."""
    bulb, _ = await async_setup_integration(menuai)

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, "src": "pir", "state": True})

    entity_id = "binary_sensor.mock_title_occupancy"
    assert entity_registry.async_get(entity_id).unique_id == f"{FAKE_MAC}_occupancy"
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, "src": "pir", "state": False})

    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_binary_sensor_restored_from_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a binary sensor restored from registry with state unknown."""
    entry = MockConfigEntry(
        domain=wiz.DOMAIN,
        unique_id=FAKE_MAC,
        data={CONF_HOST: FAKE_IP},
    )
    entry.add_to_menuai(menuai)
    bulb = _mocked_wizlight(None, None, None)

    reg_ent = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR, wiz.DOMAIN, OCCUPANCY_UNIQUE_ID.format(bulb.mac)
    )
    entity_id = reg_ent.entity_id

    with _patch_discovery(), _patch_wizlight(device=bulb):
        await async_setup_component(menuai, wiz.DOMAIN, {wiz.DOMAIN: {}})
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNKNOWN

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, "src": "pir", "state": True})

    assert entity_registry.async_get(entity_id).unique_id == f"{FAKE_MAC}_occupancy"
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_binary_sensor_never_created_no_error_on_unload(
    menuai: menuai,
) -> None:
    """Test a binary sensor does not error on unload."""
    _, entry = await async_setup_integration(menuai)
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
