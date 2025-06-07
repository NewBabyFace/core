"""The tests for automation recorder."""

from __future__ import annotations

import pytest

from menuai.components import automation
from menuai.components.automation import (
    ATTR_CUR,
    ATTR_LAST_TRIGGERED,
    ATTR_MAX,
    ATTR_MODE,
    CONF_ID,
)
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from menuai.core import menuai, ServiceCall
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_mock_service
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture
def calls(menuai: menuai) -> list[ServiceCall]:
    """Track calls to a mock service."""
    return async_mock_service(menuai, "test", "automation")


async def test_exclude_attributes(
    recorder_mock: Recorder, menuai: menuai, calls: list[ServiceCall]
) -> None:
    """Test automation registered attributes to be excluded."""
    now = dt_util.utcnow()
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"trigger": "event", "event_type": "test_event"},
                "actions": {"action": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data.get(ATTR_ENTITY_ID) == ["hello.world"]
    await async_wait_recording_done(menuai)

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) == 1
    for entity_states in states.values():
        for state in entity_states:
            assert ATTR_LAST_TRIGGERED not in state.attributes
            assert ATTR_MODE not in state.attributes
            assert ATTR_CUR not in state.attributes
            assert CONF_ID not in state.attributes
            assert ATTR_MAX not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
