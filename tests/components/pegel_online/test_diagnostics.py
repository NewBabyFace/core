"""Test pegel_online diagnostics."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.pegel_online.const import CONF_STATION, DOMAIN
from menuai.core import menuai

from . import PegelOnlineMock
from .const import (
    MOCK_CONFIG_ENTRY_DATA_DRESDEN,
    MOCK_STATION_DETAILS_DRESDEN,
    MOCK_STATION_MEASUREMENT_DRESDEN,
)

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_ENTRY_DATA_DRESDEN,
        unique_id=MOCK_CONFIG_ENTRY_DATA_DRESDEN[CONF_STATION],
    )
    entry.add_to_menuai(menuai)
    with patch("menuai.components.pegel_online.PegelOnline") as pegelonline:
        pegelonline.return_value = PegelOnlineMock(
            station_details=MOCK_STATION_DETAILS_DRESDEN,
            station_measurements=MOCK_STATION_MEASUREMENT_DRESDEN,
        )
        assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)
    assert result == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
