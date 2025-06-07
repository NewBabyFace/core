"""Test the Tado component diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.tado.const import DOMAIN
from menuai.core import menuai

from .util import async_init_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_get_config_entry_diagnostics(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test if get_config_entry_diagnostics returns the correct data."""
    await async_init_integration(menuai)

    config_entry: MockConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]
    diagnostics = await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    )
    assert diagnostics == snapshot(exclude=props("created_at", "modified_at"))
