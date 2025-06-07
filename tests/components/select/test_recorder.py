"""The tests for select recorder."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai.components import select
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.components.select import ATTR_OPTIONS
from menuai.const import ATTR_FRIENDLY_NAME, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def select_only() -> None:
    """Enable only the select platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SELECT],
    ):
        yield


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test select registered attributes to be excluded."""
    now = dt_util.utcnow()
    assert await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, select.DOMAIN, {select.DOMAIN: {"platform": "demo"}}
    )
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
            assert ATTR_OPTIONS not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
