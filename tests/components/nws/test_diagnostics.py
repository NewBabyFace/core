"""Test NWS diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.components import nws
from menuai.core import menuai

from .const import NWS_CONFIG

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_simple_nws,
) -> None:
    """Test config entry diagnostics."""

    entry = MockConfigEntry(
        domain=nws.DOMAIN,
        data=NWS_CONFIG,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert result == snapshot
