"""Tests of the times of the balboa integration."""

from __future__ import annotations

from datetime import time
from unittest.mock import MagicMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.time import (
    ATTR_TIME,
    DOMAIN as TIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform

ENTITY_TIME = "time.fakespa_"


async def test_times(
    menuai: menuai,
    client: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test spa times."""
    with patch("menuai.components.balboa.PLATFORMS", [Platform.TIME]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.parametrize(
    ("filter_cycle", "period", "value"),
    [
        (1, "start", "08:00:00"),
        (1, "end", "09:00:00"),
        (2, "start", "19:00:00"),
        (2, "end", "21:30:00"),
    ],
)
async def test_time(
    menuai: menuai, client: MagicMock, filter_cycle: int, period: str, value: str
) -> None:
    """Test spa filter cycle time."""
    await init_integration(menuai)

    time_entity = f"{ENTITY_TIME}filter_cycle_{filter_cycle}_{period}"

    # check the expected state of the time entity
    state = menuai.states.get(time_entity)
    assert state.state == value

    new_time = time(hour=7, minute=0)

    await menuai.services.async_call(
        TIME_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={ATTR_TIME: new_time},
        blocking=True,
        target={ATTR_ENTITY_ID: time_entity},
    )

    # check we made a call with the right parameters
    client.configure_filter_cycle.assert_called_with(filter_cycle, **{period: new_time})
