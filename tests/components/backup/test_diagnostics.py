"""Tests the diagnostics for MenuAI Backup integration."""

from syrupy.assertion import SnapshotAssertion

from menuai.components.backup.const import DOMAIN
from menuai.core import menuai

from .common import setup_backup_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    await setup_backup_integration(menuai, with_menuaiio=False)
    await menuai.async_block_till_done(wait_background_tasks=True)

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    diag_data = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert diag_data == snapshot
