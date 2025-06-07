"""Tests for the Elmax alarm control panels."""

from datetime import timedelta
from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.elmax.const import POLLING_SECONDS
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform

WAIT = timedelta(seconds=POLLING_SECONDS)


async def test_alarm_control_panels(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test alarm control panels."""
    with patch(
        "menuai.components.elmax.ELMAX_PLATFORMS", [Platform.ALARM_CONTROL_PANEL]
    ):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
