"""Test Reolink diagnostics."""

from unittest.mock import MagicMock

from reolink_aio.api import Chime
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    reolink_connect: MagicMock,
    test_chime: Chime,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Reolink diagnostics."""
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
    assert diag == snapshot
