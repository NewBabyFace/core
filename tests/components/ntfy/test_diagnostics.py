"""Tests for ntfy diagnostics."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.ntfy.const import DOMAIN
from menuai.const import CONF_URL
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_aiontfy")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        == snapshot
    )


@pytest.mark.usefixtures("mock_aiontfy")
async def test_diagnostics_redacted_url(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics redacted URL."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="mydomain",
        data={
            CONF_URL: "http://mydomain/",
        },
        entry_id="123456789",
        subentries_data=[],
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        == snapshot
    )
