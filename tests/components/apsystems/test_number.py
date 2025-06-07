"""Test the APSystem number module."""

import datetime
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

SCAN_INTERVAL = datetime.timedelta(seconds=30)


async def test_number(
    menuai: menuai,
    mock_apsystems: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test number command."""
    await setup_integration(menuai, mock_config_entry)
    entity_id = "number.mock_title_max_output"
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={ATTR_VALUE: 50.1},
        target={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_apsystems.set_max_power.assert_called_once_with(50)
    mock_apsystems.get_max_power.return_value = 50
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == "50"
    mock_apsystems.get_max_power.side_effect = TimeoutError()
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={ATTR_VALUE: 50.1},
        target={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("mock_apsystems")
@patch("menuai.components.apsystems.PLATFORMS", [Platform.NUMBER])
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
