"""Test pushbullet integration."""

from unittest.mock import MagicMock, patch

from pushover_complete import BadAPIRequestError
import pytest
import requests_mock
from urllib3.exceptions import MaxRetryError

from menuai.components.pushover.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.fixture(autouse=False)
def mock_pushover():
    """Mock pushover."""
    with patch(
        "pushover_complete.PushoverAPI._generic_post", return_value={}
    ) as mock_generic_post:
        yield mock_generic_post


async def test_async_setup_entry_success(
    menuai: menuai, mock_pushover: MagicMock
) -> None:
    """Test pushover successful setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_unique_id_updated(menuai: menuai, mock_pushover: MagicMock) -> None:
    """Test updating unique_id to new format."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="MYUSERKEY")
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id is None


async def test_async_setup_entry_failed_invalid_api_key(
    menuai: menuai, mock_pushover: MagicMock
) -> None:
    """Test pushover failed setup due to invalid api key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    mock_pushover.side_effect = BadAPIRequestError("400: application token is invalid")
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_async_setup_entry_failed_conn_error(
    menuai: menuai, mock_pushover: MagicMock
) -> None:
    """Test pushover failed setup due to conn error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    mock_pushover.side_effect = BadAPIRequestError
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_setup_entry_failed_json_error(
    menuai: menuai, requests_mock: requests_mock.Mocker
) -> None:
    """Test pushover failed setup due to bad json response from library."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    requests_mock.post(
        "https://api.pushover.net/1/users/validate.json", status_code=204
    )
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_setup_entry_failed_urrlib3_error(
    menuai: menuai, mock_pushover: MagicMock
) -> None:
    """Test pushover failed setup due to conn error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    mock_pushover.side_effect = MaxRetryError(MagicMock(), MagicMock())
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
