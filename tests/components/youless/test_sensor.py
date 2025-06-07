"""Test the sensor classes for youless."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_component

from tests.common import snapshot_platform


async def test_sensors(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test the sensor classes for youless."""
    with patch("menuai.components.youless.PLATFORMS", [Platform.SENSOR]):
        entry = await init_component(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
