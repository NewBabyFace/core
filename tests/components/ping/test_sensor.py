"""Test sensor platform of Ping."""

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai
from menuai.helpers import entity_registry as er


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "setup_integration")
@pytest.mark.parametrize(
    "sensor_name",
    [
        "round_trip_time_average",
        "round_trip_time_maximum",
        "round_trip_time_mean_deviation",  # should be None in the snapshot
        "round_trip_time_minimum",
    ],
)
async def test_setup_and_update(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    sensor_name: str,
) -> None:
    """Test sensor setup and update."""

    entry = entity_registry.async_get(f"sensor.10_10_10_10_{sensor_name}")
    assert entry == snapshot(exclude=props("unique_id"))

    state = menuai.states.get(f"sensor.10_10_10_10_{sensor_name}")
    assert state == snapshot
