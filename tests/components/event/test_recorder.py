"""The tests for event recorder."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from menuai.components import select
from menuai.components.event import ATTR_EVENT_TYPES
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.const import ATTR_FRIENDLY_NAME, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def event_only() -> None:
    """Enable only the event platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.EVENT],
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
    menuai.bus.async_fire("demo_button_pressed")
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert state
            assert ATTR_EVENT_TYPES not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
