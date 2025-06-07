"""The tests for recorder platform."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.recorder.history import get_significant_states
from menuai.components.schedule.const import ATTR_NEXT_EVENT, DOMAIN
from menuai.const import ATTR_EDITABLE, ATTR_FRIENDLY_NAME, ATTR_ICON
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.mark.usefixtures("recorder_mock", "enable_custom_integrations")
async def test_exclude_attributes(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test attributes to be excluded."""
    freezer.move_to("2024-08-02 06:30:00-07:00")  # Before Friday event
    now = dt_util.utcnow()
    assert await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {
                "test": {
                    "name": "Party mode",
                    "icon": "mdi:party-popper",
                    "monday": [{"from": "1:00", "to": "2:00"}],
                    "tuesday": [{"from": "2:00", "to": "3:00"}],
                    "wednesday": [{"from": "3:00", "to": "4:00"}],
                    "thursday": [{"from": "5:00", "to": "6:00"}],
                    "friday": [
                        {"from": "7:00", "to": "8:00", "data": {"party_level": "epic"}}
                    ],
                    "saturday": [{"from": "9:00", "to": "10:00"}],
                    "sunday": [
                        {"from": "11:00", "to": "12:00", "data": {"entry": "VIPs only"}}
                    ],
                }
            }
        },
    )

    state = menuai.states.get("schedule.test")
    assert state
    assert state.attributes[ATTR_EDITABLE] is False
    assert state.attributes[ATTR_FRIENDLY_NAME]
    assert state.attributes[ATTR_ICON]
    assert state.attributes[ATTR_NEXT_EVENT]

    # Move to during Friday event
    freezer.move_to("2024-08-02 07:30:00-07:00")
    async_fire_time_changed(menuai, fire_all=True)
    await menuai.async_block_till_done()
    state = menuai.states.get("schedule.test")
    assert "entry" not in state.attributes
    assert state.attributes["party_level"] == "epic"

    # Move to during Sunday event
    freezer.move_to("2024-08-04 11:30:00-07:00")
    async_fire_time_changed(menuai, fire_all=True)
    await menuai.async_block_till_done()
    state = menuai.states.get("schedule.test")
    assert "party_level" not in state.attributes
    assert state.attributes["entry"] == "VIPs only"

    await menuai.async_block_till_done()
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert ATTR_EDITABLE not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
            assert ATTR_ICON in state.attributes
            assert ATTR_NEXT_EVENT not in state.attributes
            assert "entry" not in state.attributes
            assert "party_level" not in state.attributes
