"""Tests for the Nextcloud coordinator."""

from unittest.mock import Mock, patch

from freezegun.api import FrozenDateTimeFactory
from nextcloudmonitor import (
    NextcloudMonitor,
    NextcloudMonitorAuthorizationError,
    NextcloudMonitorConnectionError,
    NextcloudMonitorError,
    NextcloudMonitorRequestError,
)
import pytest

from menuai.components.nextcloud.const import DEFAULT_SCAN_INTERVAL
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import mock_config_entry
from .const import NC_DATA, VALID_CONFIG

from tests.common import async_fire_time_changed


@pytest.mark.parametrize(
    ("error"),
    [
        (NextcloudMonitorAuthorizationError),
        (NextcloudMonitorConnectionError),
        (NextcloudMonitorRequestError),
    ],
)
async def test_data_update(
    menuai: menuai, freezer: FrozenDateTimeFactory, error: NextcloudMonitorError
) -> None:
    """Test a coordinator data updates."""
    entry = mock_config_entry(VALID_CONFIG)
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.nextcloud.NextcloudMonitor", spec=NextcloudMonitor
        ) as mock_nextcloud_monitor,
    ):
        mock_nextcloud_monitor.return_value.update = Mock(
            return_value=True,
            side_effect=[None, error, None],
        )
        mock_nextcloud_monitor.return_value.data = NC_DATA
        assert await menuai.config_entries.async_setup(entry.entry_id)

        # Test successful setup and first data fetch
        await menuai.async_block_till_done(wait_background_tasks=True)
        states = menuai.states.async_all()
        assert (state != STATE_UNAVAILABLE for state in states)

        # Test states get unavailable on error
        freezer.tick(DEFAULT_SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        states = menuai.states.async_all()
        assert (state == STATE_UNAVAILABLE for state in states)

        # Test successful data fetch
        freezer.tick(DEFAULT_SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        states = menuai.states.async_all()
        assert (state != STATE_UNAVAILABLE for state in states)
