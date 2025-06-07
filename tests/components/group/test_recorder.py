"""The tests for group recorder."""

from __future__ import annotations

from datetime import timedelta

import pytest

from menuai.components import group
from menuai.components.group import ATTR_AUTO, ATTR_ENTITY_ID, ATTR_ORDER
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.const import ATTR_FRIENDLY_NAME, STATE_ON
from menuai.core import menuai, split_entity_id
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def setup_menuai():
    """Override the fixture in group.conftest."""


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test number registered attributes to be excluded."""
    now = dt_util.utcnow()
    menuai.states.async_set("light.bowl", STATE_ON)

    assert await async_setup_component(menuai, "light", {})
    assert await async_setup_component(
        menuai,
        group.DOMAIN,
        {
            group.DOMAIN: {
                "group_zero": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_one": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_two": {"entities": "light.Bowl", "icon": "mdi:work"},
            }
        },
    )
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) > 1
    for entity_states in states.values():
        for state in entity_states:
            if split_entity_id(state.entity_id)[0] == group.DOMAIN:
                assert ATTR_AUTO not in state.attributes
                assert ATTR_ENTITY_ID not in state.attributes
                assert ATTR_ORDER not in state.attributes
                assert ATTR_FRIENDLY_NAME in state.attributes
