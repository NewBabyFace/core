"""The tests for light recorder."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai.components import light
from menuai.components.light import (
    _DEPRECATED_ATTR_COLOR_TEMP,
    _DEPRECATED_ATTR_MAX_MIREDS,
    _DEPRECATED_ATTR_MIN_MIREDS,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_XY_COLOR,
    DOMAIN,
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
async def light_only() -> None:
    """Enable only the light platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.LIGHT],
    ):
        yield


async def test_exclude_attributes(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test light registered attributes to be excluded."""
    now = dt_util.utcnow()
    assert await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, light.DOMAIN, {light.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids(DOMAIN)
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert _DEPRECATED_ATTR_MIN_MIREDS.value not in state.attributes
            assert _DEPRECATED_ATTR_MAX_MIREDS.value not in state.attributes
            assert ATTR_SUPPORTED_COLOR_MODES not in state.attributes
            assert ATTR_EFFECT_LIST not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
            assert ATTR_MAX_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_MIN_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_BRIGHTNESS not in state.attributes
            assert ATTR_COLOR_MODE not in state.attributes
            assert _DEPRECATED_ATTR_COLOR_TEMP.value not in state.attributes
            assert ATTR_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_EFFECT not in state.attributes
            assert ATTR_HS_COLOR not in state.attributes
            assert ATTR_RGB_COLOR not in state.attributes
            assert ATTR_RGBW_COLOR not in state.attributes
            assert ATTR_RGBWW_COLOR not in state.attributes
            assert ATTR_XY_COLOR not in state.attributes
