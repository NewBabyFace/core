"""Tests for the LaMetric helpers."""

from unittest.mock import MagicMock

import pytest

from menuai.components.lametric.helpers import async_get_coordinator_by_device_id
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_get_coordinator_by_device_id(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    mock_lametric: MagicMock,
) -> None:
    """Test get LaMetric coordinator by device ID ."""
    with pytest.raises(ValueError, match="Unknown LaMetric device ID: bla"):
        async_get_coordinator_by_device_id(menuai, "bla")

    entry = entity_registry.async_get("button.frenck_s_lametric_next_app")
    assert entry
    assert entry.device_id

    coordinator = async_get_coordinator_by_device_id(menuai, entry.device_id)
    assert coordinator.data == mock_lametric.device.return_value

    # Unload entry
    await menuai.config_entries.async_unload(init_integration.entry_id)
    await menuai.async_block_till_done()

    with pytest.raises(
        ValueError, match=f"No coordinator for device ID: {entry.device_id}"
    ):
        async_get_coordinator_by_device_id(menuai, entry.device_id)
