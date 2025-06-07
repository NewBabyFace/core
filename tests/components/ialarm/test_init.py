"""Test the Antifurto365 iAlarm init."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from menuai.components.ialarm.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture(name="ialarm_api")
def ialarm_api_fixture():
    """Set up IAlarm API fixture."""
    with patch("menuai.components.ialarm.IAlarm") as mock_ialarm_api:
        yield mock_ialarm_api


@pytest.fixture(name="mock_config_entry")
def mock_config_fixture():
    """Return a fake config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.10.20", CONF_PORT: 18034},
        entry_id=str(uuid4()),
    )


async def test_setup_entry(menuai: menuai, ialarm_api, mock_config_entry) -> None:
    """Test setup entry."""
    ialarm_api.return_value.get_mac = Mock(return_value="00:00:54:12:34:56")

    mock_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    ialarm_api.return_value.get_mac.assert_called_once()
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_not_ready(
    menuai: menuai, ialarm_api, mock_config_entry
) -> None:
    """Test setup failed because we can't connect to the alarm system."""
    ialarm_api.return_value.get_mac = Mock(side_effect=ConnectionError)

    mock_config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai, ialarm_api, mock_config_entry) -> None:
    """Test being able to unload an entry."""
    ialarm_api.return_value.get_mac = Mock(return_value="00:00:54:12:34:56")

    mock_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
