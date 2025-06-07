"""Tests for Starlink diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.components.starlink.const import DOMAIN
from menuai.const import CONF_IP_ADDRESS
from menuai.core import menuai

from .patchers import (
    HISTORY_STATS_SUCCESS_PATCHER,
    LOCATION_DATA_SUCCESS_PATCHER,
    SLEEP_DATA_SUCCESS_PATCHER,
    STATUS_DATA_SUCCESS_PATCHER,
)

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IP_ADDRESS: "1.2.3.4:0000"},
    )

    with (
        STATUS_DATA_SUCCESS_PATCHER,
        LOCATION_DATA_SUCCESS_PATCHER,
        SLEEP_DATA_SUCCESS_PATCHER,
        HISTORY_STATS_SUCCESS_PATCHER,
    ):
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        diag = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

        assert diag == snapshot
