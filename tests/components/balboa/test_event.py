"""Tests of the events of the balboa integration."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.event import ATTR_EVENT_TYPE
from menuai.const import STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform

ENTITY_EVENT = "event.fakespa_fault"
FAULT_DATE = "fault_date"


async def test_events(
    menuai: menuai,
    client: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test spa events."""
    with patch("menuai.components.balboa.PLATFORMS", [Platform.EVENT]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_event(menuai: menuai, client: MagicMock) -> None:
    """Test spa fault event."""
    await init_integration(menuai)

    # check the state is unknown
    state = menuai.states.get(ENTITY_EVENT)
    assert state.state == STATE_UNKNOWN

    # set a fault
    client.fault = MagicMock(
        fault_datetime=datetime(2025, 2, 15, 13, 0), message_code=16
    )
    client.emit("")
    await menuai.async_block_till_done()

    # check new state is what we expect
    state = menuai.states.get(ENTITY_EVENT)
    assert state.attributes[ATTR_EVENT_TYPE] == "low_flow"
    assert state.attributes[FAULT_DATE] == "2025-02-15T13:00:00"
    assert state.attributes["code"] == 16

    # set fault to None
    client.fault = None
    client.emit("")
    await menuai.async_block_till_done()

    # validate state remains unchanged
    state = menuai.states.get(ENTITY_EVENT)
    assert state.attributes[ATTR_EVENT_TYPE] == "low_flow"
    assert state.attributes[FAULT_DATE] == "2025-02-15T13:00:00"
    assert state.attributes["code"] == 16

    # set fault to an unknown one
    client.fault = MagicMock(
        fault_datetime=datetime(2025, 2, 15, 14, 0), message_code=-1
    )
    # validate a ValueError is raises
    with pytest.raises(ValueError):
        client.emit("")
    await menuai.async_block_till_done()

    # validate state remains unchanged
    state = menuai.states.get(ENTITY_EVENT)
    assert state.attributes[ATTR_EVENT_TYPE] == "low_flow"
    assert state.attributes[FAULT_DATE] == "2025-02-15T13:00:00"
    assert state.attributes["code"] == 16
