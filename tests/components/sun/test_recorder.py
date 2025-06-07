"""The tests for sun recorder."""

from __future__ import annotations

from datetime import timedelta

from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.components.sun import DOMAIN
from menuai.components.sun.entity import (
    STATE_ATTR_AZIMUTH,
    STATE_ATTR_ELEVATION,
    STATE_ATTR_NEXT_DAWN,
    STATE_ATTR_NEXT_DUSK,
    STATE_ATTR_NEXT_MIDNIGHT,
    STATE_ATTR_NEXT_NOON,
    STATE_ATTR_NEXT_RISING,
    STATE_ATTR_NEXT_SETTING,
    STATE_ATTR_RISING,
)
from menuai.const import ATTR_FRIENDLY_NAME
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test sun attributes to be excluded."""
    now = dt_util.utcnow()
    await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert STATE_ATTR_AZIMUTH not in state.attributes
            assert STATE_ATTR_ELEVATION not in state.attributes
            assert STATE_ATTR_NEXT_DAWN not in state.attributes
            assert STATE_ATTR_NEXT_DUSK not in state.attributes
            assert STATE_ATTR_NEXT_MIDNIGHT not in state.attributes
            assert STATE_ATTR_NEXT_NOON not in state.attributes
            assert STATE_ATTR_NEXT_RISING not in state.attributes
            assert STATE_ATTR_NEXT_SETTING not in state.attributes
            assert STATE_ATTR_RISING not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
