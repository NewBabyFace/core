"""The tests for update recorder."""

from __future__ import annotations

from datetime import timedelta

import pytest

from menuai.components.person import ATTR_DEVICE_TRACKERS, DOMAIN
from menuai.components.recorder.history import get_significant_states
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockUser, async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.mark.usefixtures("recorder_mock", "enable_custom_integrations")
async def test_exclude_attributes(
    menuai: menuai,
    menuai_admin_user: MockUser,
    storage_setup,
) -> None:
    """Test update attributes to be excluded."""
    now = dt_util.utcnow()
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "test person",
            "user_id": "test_user_id",
            "device_trackers": ["device_tracker.test"],
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)

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
            assert ATTR_DEVICE_TRACKERS not in state.attributes
