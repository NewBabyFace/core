"""Tests for the sensor platform of the A. O. Smith integration."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
async def platforms() -> AsyncGenerator[None]:
    """Return the platforms to be loaded for this test."""
    with patch("menuai.components.aosmith.PLATFORMS", [Platform.SENSOR]):
        yield


async def test_state(
    menuai: menuai,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the state of the sensor entities."""
    await snapshot_platform(menuai, entity_registry, snapshot, init_integration.entry_id)
