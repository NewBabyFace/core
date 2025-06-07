"""Test for diagnostics platform of the Bring! integration."""

from unittest.mock import AsyncMock

from bring_api import BringItemsResponse
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.bring.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry, async_load_fixture
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_bring_client")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    bring_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_bring_client: AsyncMock,
) -> None:
    """Test diagnostics."""
    mock_bring_client.get_list.side_effect = [
        BringItemsResponse.from_json(
            await async_load_fixture(menuai, "items.json", DOMAIN)
        ),
        BringItemsResponse.from_json(
            await async_load_fixture(menuai, "items2.json", DOMAIN)
        ),
    ]
    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, bring_config_entry)
        == snapshot
    )
