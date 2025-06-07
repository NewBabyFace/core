"""The tests for script recorder."""

from __future__ import annotations

import pytest

from menuai.components import script
from menuai.components.recorder import Recorder
from menuai.components.recorder.history import get_significant_states
from menuai.components.script import (
    ATTR_CUR,
    ATTR_LAST_ACTION,
    ATTR_LAST_TRIGGERED,
    ATTR_MAX,
    ATTR_MODE,
)
from menuai.const import ATTR_FRIENDLY_NAME
from menuai.core import Context, menuai, ServiceCall, callback
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
    await menuai.async_block_till_done()
    calls = []
    context = Context()

    @callback
    def record_call(service):
        """Add recorded event to set."""
        calls.append(service)

    menuai.services.async_register("test", "script", record_call)

    assert await async_setup_component(
        menuai,
        "script",
        {
            "script": {
                "test": {
                    "sequence": {
                        "action": "test.script",
                        "data_template": {"hello": "{{ greeting }}"},
                    }
                }
            }
        },
    )

    await menuai.services.async_call(
        script.DOMAIN, "test", {"greeting": "world"}, context=context
    )
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)
    assert len(calls) == 1

    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, menuai.states.async_entity_ids()
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert ATTR_LAST_TRIGGERED not in state.attributes
            assert ATTR_MODE not in state.attributes
            assert ATTR_CUR not in state.attributes
            assert ATTR_LAST_ACTION not in state.attributes
            assert ATTR_MAX not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
