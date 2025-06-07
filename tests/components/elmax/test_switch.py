"""Tests for the Elmax switches."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform


async def test_switches(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test switches."""
    with patch("menuai.components.elmax.ELMAX_PLATFORMS", [Platform.SWITCH]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
