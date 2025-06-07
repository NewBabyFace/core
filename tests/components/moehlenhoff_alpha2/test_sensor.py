"""Tests for the Moehlenhoff Alpha2 sensors."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform


async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test sensors."""
    with patch(
        "menuai.components.moehlenhoff_alpha2.PLATFORMS",
        [Platform.SENSOR],
    ):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
