"""Tests of the switches of the balboa integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform
from tests.components.switch import common

ENTITY_SWITCH = "switch.fakespa_filter_cycle_2_enabled"


async def test_switches(
    menuai: menuai,
    client: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test spa switches."""
    with patch("menuai.components.balboa.PLATFORMS", [Platform.SWITCH]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_switch(menuai: menuai, client: MagicMock) -> None:
    """Test spa filter cycle enabled switch."""
    await init_integration(menuai)

    # check if the initial state is on
    state = menuai.states.get(ENTITY_SWITCH)
    assert state.state == STATE_ON

    # test calling turn off
    await common.async_turn_off(menuai, ENTITY_SWITCH)
    client.configure_filter_cycle.assert_called_with(2, enabled=False)

    setattr(client, "filter_cycle_2_enabled", False)
    client.emit("")
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_SWITCH)
    assert state.state == STATE_OFF

    # test calling turn on
    await common.async_turn_on(menuai, ENTITY_SWITCH)
    client.configure_filter_cycle.assert_called_with(2, enabled=True)
