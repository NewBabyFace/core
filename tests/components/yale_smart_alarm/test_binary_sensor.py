"""The test for the Yale Smart Alarm binary sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.BINARY_SENSOR]],
)
async def test_binary_sensor(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Yale Smart Alarm binary sensor."""
    entry = load_config_entry[0]
    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
