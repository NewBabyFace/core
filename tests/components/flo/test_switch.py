"""Tests for the switch domain for Flo by Moen."""

import pytest

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_valve_switches(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test Flo by Moen valve switches."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    entity_id = "switch.smart_water_shutoff_shutoff_valve"
    assert menuai.states.get(entity_id).state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_off", {"entity_id": entity_id}, blocking=True
    )
    assert menuai.states.get(entity_id).state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert menuai.states.get(entity_id).state == STATE_ON
