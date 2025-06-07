"""Test the laundrify coordinator."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from laundrify_aio import LaundrifyDevice, exceptions

from menuai.components.laundrify.const import DEFAULT_POLL_INTERVAL
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai, State
from menuai.util import slugify

from tests.common import async_fire_time_changed


def get_coord_entity(menuai: menuai, mock_device: LaundrifyDevice) -> State:
    """Get the coordinated energy sensor entity."""
    device_slug = slugify(mock_device.name, separator="_")
    return menuai.states.get(f"sensor.{device_slug}_energy")


async def test_coordinator_update_success(
    menuai: menuai,
    laundrify_config_entry,
    mock_device: LaundrifyDevice,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the coordinator update is performed successfully."""
    freezer.tick(timedelta(seconds=DEFAULT_POLL_INTERVAL))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    coord_entity = get_coord_entity(menuai, mock_device)
    assert coord_entity.state != STATE_UNAVAILABLE


async def test_coordinator_update_unauthorized(
    menuai: menuai,
    laundrify_config_entry,
    laundrify_api_mock,
    mock_device: LaundrifyDevice,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the coordinator update fails if an UnauthorizedException is thrown."""
    laundrify_api_mock.get_machines.side_effect = exceptions.UnauthorizedException

    freezer.tick(timedelta(seconds=DEFAULT_POLL_INTERVAL))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    coord_entity = get_coord_entity(menuai, mock_device)
    assert coord_entity.state == STATE_UNAVAILABLE


async def test_coordinator_update_connection_failed(
    menuai: menuai,
    laundrify_config_entry,
    laundrify_api_mock,
    mock_device: LaundrifyDevice,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the coordinator update fails if an ApiConnectionException is thrown."""
    laundrify_api_mock.get_machines.side_effect = exceptions.ApiConnectionException

    freezer.tick(timedelta(seconds=DEFAULT_POLL_INTERVAL))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    coord_entity = get_coord_entity(menuai, mock_device)
    assert coord_entity.state == STATE_UNAVAILABLE
