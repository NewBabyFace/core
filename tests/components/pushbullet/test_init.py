"""Test pushbullet integration."""

from unittest.mock import patch

from pushbullet import InvalidKeyError, PushbulletError

from menuai.components.pushbullet.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_START
from menuai.core import menuai

from . import MOCK_CONFIG

from tests.common import MockConfigEntry


async def test_async_setup_entry_success(
    menuai: menuai, requests_mock_fixture
) -> None:
    """Test pushbullet successful setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.pushbullet.api.PushBulletNotificationProvider.start"
    ) as mock_start:
        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        mock_start.assert_called_once()


async def test_setup_entry_failed_invalid_key(menuai: menuai) -> None:
    """Test pushbullet failed setup due to invalid key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.pushbullet.PushBullet",
        side_effect=InvalidKeyError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_failed_conn_error(menuai: menuai) -> None:
    """Test pushbullet failed setup due to conn error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.pushbullet.PushBullet",
        side_effect=PushbulletError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_unload_entry(menuai: menuai, requests_mock_fixture) -> None:
    """Test pushbullet unload entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
