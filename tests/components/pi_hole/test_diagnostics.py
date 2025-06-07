"""Test pi_hole component."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components import pi_hole
from menuai.core import menuai

from . import CONFIG_DATA_DEFAULTS, _create_mocked_hole, _patch_init_hole

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Tests diagnostics."""
    mocked_hole = _create_mocked_hole()
    entry = MockConfigEntry(
        domain=pi_hole.DOMAIN, data=CONFIG_DATA_DEFAULTS, entry_id="pi_hole_mock_entry"
    )
    entry.add_to_menuai(menuai)
    with _patch_init_hole(mocked_hole):
        assert await menuai.config_entries.async_setup(entry.entry_id)

    await menuai.async_block_till_done()

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot(
        exclude=props("created_at", "modified_at")
    )
