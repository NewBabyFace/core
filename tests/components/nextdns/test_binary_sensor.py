"""Test binary sensor of NextDNS integration."""

from datetime import timedelta
from unittest.mock import patch

from nextdns import ApiError
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_ON, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from . import init_integration, mock_nextdns

from tests.common import async_fire_time_changed, snapshot_platform


async def test_binary_sensor(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test states of the binary sensors."""
    with patch("menuai.components.nextdns.PLATFORMS", [Platform.BINARY_SENSOR]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_availability(menuai: menuai) -> None:
    """Ensure that we mark the entities unavailable correctly when service causes an error."""
    await init_integration(menuai)

    state = menuai.states.get("binary_sensor.fake_profile_device_connection_status")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == STATE_ON

    future = utcnow() + timedelta(minutes=10)
    with patch(
        "menuai.components.nextdns.NextDns.connection_status",
        side_effect=ApiError("API Error"),
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("binary_sensor.fake_profile_device_connection_status")
    assert state
    assert state.state == STATE_UNAVAILABLE

    future = utcnow() + timedelta(minutes=20)
    with mock_nextdns():
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("binary_sensor.fake_profile_device_connection_status")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == STATE_ON
