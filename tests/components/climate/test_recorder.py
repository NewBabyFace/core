"""The tests for climate recorder."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai.components import climate
from menuai.components.climate import (
    ATTR_FAN_MODES,
    ATTR_HVAC_MODES,
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODES,
    ATTR_SWING_MODES,
    ATTR_TARGET_TEMP_STEP,
)
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.const import ATTR_FRIENDLY_NAME, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def climate_only() -> None:
    """Enable only the climate platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.CLIMATE],
    ):
        yield


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test climate registered attributes to be excluded."""
    now = dt_util.utcnow()
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, climate.DOMAIN, {climate.DOMAIN: {"platform": "demo"}}
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
            assert ATTR_PRESET_MODES not in state.attributes
            assert ATTR_HVAC_MODES not in state.attributes
            assert ATTR_FAN_MODES not in state.attributes
            assert ATTR_SWING_MODES not in state.attributes
            assert ATTR_MIN_TEMP not in state.attributes
            assert ATTR_MAX_TEMP not in state.attributes
            assert ATTR_MIN_HUMIDITY not in state.attributes
            assert ATTR_MAX_HUMIDITY not in state.attributes
            assert ATTR_TARGET_TEMP_STEP not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
