"""Test Météo France weather entity."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.meteo_france.PLATFORMS", [Platform.WEATHER]):
        yield


async def test_weather(
    menuai: menuai,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the weather entity."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)
