"""Tests for the Rituals Perfume Genie switch platform."""

from __future__ import annotations

from menuai.components.menuai import SERVICE_UPDATE_ENTITY
from menuai.components.rituals_perfume_genie.const import DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from .common import (
    init_integration,
    mock_config_entry,
    mock_diffuser_v1_battery_cartridge,
)


async def test_switch_entity(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test the creation and values of the Rituals Perfume Genie diffuser switch."""
    config_entry = mock_config_entry(unique_id="id_123_switch_test")
    diffuser = mock_diffuser_v1_battery_cartridge()
    await init_integration(menuai, config_entry, [diffuser])

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_ON

    entry = entity_registry.async_get("switch.genie")
    assert entry
    assert entry.unique_id == f"{diffuser.hublot}-is_on"


async def test_switch_handle_coordinator_update(menuai: menuai) -> None:
    """Test handling a coordinator update."""
    config_entry = mock_config_entry(unique_id="switch_handle_coordinator_update_test")
    diffuser = mock_diffuser_v1_battery_cartridge()
    await init_integration(menuai, config_entry, [diffuser])
    await async_setup_component(menuai, "menuai", {})
    coordinator = menuai.data[DOMAIN][config_entry.entry_id]["lot123v1"]
    diffuser.is_on = False

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_ON

    call_count_before_update = diffuser.update_data.call_count

    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["switch.genie"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_OFF

    assert coordinator.last_update_success
    assert diffuser.update_data.call_count == call_count_before_update + 1


async def test_set_switch_state(menuai: menuai) -> None:
    """Test changing the diffuser switch entity state."""
    config_entry = mock_config_entry(unique_id="id_123_switch_set_state_test")
    await init_integration(menuai, config_entry, [mock_diffuser_v1_battery_cartridge()])

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.genie"},
        blocking=True,
    )

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.genie"},
        blocking=True,
    )

    state = menuai.states.get("switch.genie")
    assert state
    assert state.state == STATE_ON
