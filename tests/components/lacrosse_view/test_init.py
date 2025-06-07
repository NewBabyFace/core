"""Test the LaCrosse View initialization."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from lacrosse_view import HTTPError, LoginError

from menuai.components.lacrosse_view.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import MOCK_ENTRY_DATA, TEST_SENSOR

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_unload_entry(menuai: menuai) -> None:
    """Test the unload entry."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    sensor = TEST_SENSOR.model_copy()
    status = sensor.data
    sensor.data = None

    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True),
        patch(
            "lacrosse_view.LaCrosse.get_devices",
            return_value=[sensor],
        ),
        patch("lacrosse_view.LaCrosse.get_sensor_status", return_value=status),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.data[DOMAIN]

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entries[0].entry_id)
    await menuai.async_block_till_done()
    assert entries[0].state is ConfigEntryState.NOT_LOADED


async def test_login_error(menuai: menuai) -> None:
    """Test login error."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    with patch("lacrosse_view.LaCrosse.login", side_effect=LoginError("Test")):
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.SETUP_ERROR
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"


async def test_http_error(menuai: menuai) -> None:
    """Test http error."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True),
        patch("lacrosse_view.LaCrosse.get_devices", side_effect=HTTPError),
    ):
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.SETUP_RETRY

    config_entry_2 = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry_2.add_to_menuai(menuai)

    # Start over, let get_devices succeed but get_sensor_status fail
    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True),
        patch("lacrosse_view.LaCrosse.get_devices", return_value=[TEST_SENSOR]),
        patch("lacrosse_view.LaCrosse.get_sensor_status", side_effect=HTTPError),
    ):
        assert not await menuai.config_entries.async_setup(config_entry_2.entry_id)
        await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 2
    assert entries[1].state is ConfigEntryState.SETUP_RETRY


async def test_new_token(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Test new token."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    sensor = TEST_SENSOR.model_copy()
    status = sensor.data
    sensor.data = None

    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True) as login,
        patch(
            "lacrosse_view.LaCrosse.get_devices",
            return_value=[sensor],
        ),
        patch("lacrosse_view.LaCrosse.get_sensor_status", return_value=status),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        login.assert_called_once()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True) as login,
        patch(
            "lacrosse_view.LaCrosse.get_devices",
            return_value=[TEST_SENSOR],
        ),
    ):
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        login.assert_called_once()


async def test_failed_token(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test if a reauth flow occurs when token refresh fails."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    sensor = TEST_SENSOR.model_copy()
    status = sensor.data
    sensor.data = None

    with (
        patch("lacrosse_view.LaCrosse.login", return_value=True) as login,
        patch(
            "lacrosse_view.LaCrosse.get_devices",
            return_value=[sensor],
        ),
        patch("lacrosse_view.LaCrosse.get_sensor_status", return_value=status),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        login.assert_called_once()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    with patch("lacrosse_view.LaCrosse.login", side_effect=LoginError("Test")):
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"
