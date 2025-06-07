"""Tests for the Android IP Webcam integration."""

from unittest.mock import Mock

import aiohttp

from menuai.components.android_ip_webcam.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_CONFIG_DATA = {
    "name": "IP Webcam",
    "host": "1.1.1.1",
    "port": 8080,
    "username": "user",
    "password": "pass",
}


async def test_successful_config_entry(
    menuai: menuai, aioclient_mock_fixture
) -> None:
    """Test settings up integration from config entry."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED


async def test_setup_failed_connection_error(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test integration failed due to connection error."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA)
    entry.add_to_menuai(menuai)
    aioclient_mock.get(
        "http://1.1.1.1:8080/status.json?show_avail=1",
        exc=aiohttp.ClientError,
    )

    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_failed_invalid_auth(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test integration failed due to invalid auth."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA)
    entry.add_to_menuai(menuai)
    aioclient_mock.get(
        "http://1.1.1.1:8080/status.json?show_avail=1",
        exc=aiohttp.ClientResponseError(Mock(), (), status=401),
    )

    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai, aioclient_mock_fixture) -> None:
    """Test removing integration."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
