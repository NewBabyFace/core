"""Test the Fast.com component diagnostics."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.fastdotcom.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_get_config_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test if get_config_entry_diagnostics returns the correct data."""
    config_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title=DEFAULT_NAME,
        source=SOURCE_USER,
        options={},
        entry_id="TEST_ENTRY_ID",
        unique_id="UNIQUE_TEST_ID",
        minor_version=1,
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.fastdotcom.coordinator.fast_com", return_value=50.3
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        == snapshot
    )
