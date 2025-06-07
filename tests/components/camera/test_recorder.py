"""The tests for camera recorder."""

from __future__ import annotations

from datetime import timedelta

import pytest

from menuai.components import camera
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.const import (
    ATTR_ATTRIBUTION,
    ATTR_ENTITY_PICTURE,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
)
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def setup_menuai():
    """Override the fixture in calendar.conftest."""


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test camera registered attributes to be excluded."""
    now = dt_util.utcnow()
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
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
            assert "access_token" not in state.attributes
            assert ATTR_ENTITY_PICTURE not in state.attributes
            assert ATTR_ATTRIBUTION not in state.attributes
            assert ATTR_SUPPORTED_FEATURES not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
