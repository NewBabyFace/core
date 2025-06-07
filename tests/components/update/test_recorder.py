"""The tests for update recorder."""

from __future__ import annotations

from datetime import timedelta

from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.components.update.const import (
    ATTR_DISPLAY_PRECISION,
    ATTR_IN_PROGRESS,
    ATTR_INSTALLED_VERSION,
    ATTR_RELEASE_SUMMARY,
    ATTR_UPDATE_PERCENTAGE,
    DOMAIN,
)
from menuai.const import ATTR_ENTITY_PICTURE, CONF_PLATFORM
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from .common import MockUpdateEntity

from tests.common import async_fire_time_changed, setup_test_component_platform
from tests.components.recorder.common import async_wait_recording_done


async def test_exclude_attributes(
    recorder_mock: Recorder,
    menuai: menuai,
    mock_update_entities: list[MockUpdateEntity],
) -> None:
    """Test update attributes to be excluded."""
    now = dt_util.utcnow()
    setup_test_component_platform(menuai, DOMAIN, mock_update_entities)
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()
    state = menuai.states.get("update.update_already_in_progress")
    assert state.attributes[ATTR_DISPLAY_PRECISION] == 0
    assert state.attributes[ATTR_IN_PROGRESS] is True
    assert state.attributes[ATTR_UPDATE_PERCENTAGE] == 50
    assert (
        state.attributes[ATTR_ENTITY_PICTURE]
        == "https://brands.home-assistant.io/_/test/icon.png"
    )
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
            assert ATTR_DISPLAY_PRECISION not in state.attributes
            assert ATTR_ENTITY_PICTURE not in state.attributes
            assert ATTR_IN_PROGRESS not in state.attributes
            assert ATTR_RELEASE_SUMMARY not in state.attributes
            assert ATTR_INSTALLED_VERSION in state.attributes
            assert ATTR_UPDATE_PERCENTAGE not in state.attributes
