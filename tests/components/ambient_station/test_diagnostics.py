"""Test Ambient PWS diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.ambient_station import AmbientStationConfigEntry
from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    config_entry: AmbientStationConfigEntry,
    menuai_client: ClientSessionGenerator,
    data_station,
    setup_config_entry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    ambient = config_entry.runtime_data
    ambient.stations = data_station
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
