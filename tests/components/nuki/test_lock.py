"""Tests for the nuki locks."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform


async def test_locks(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test locks."""
    with patch("menuai.components.nuki.PLATFORMS", [Platform.LOCK]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
