"""Tests for wiz integration."""

import datetime
from unittest.mock import AsyncMock, patch

from menuai.components.wiz.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_FRIENDLY_NAME, CONF_HOST, EVENT_menuai_STOP
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import (
    FAKE_IP,
    FAKE_MAC,
    FAKE_SOCKET,
    _mocked_wizlight,
    _patch_discovery,
    _patch_wizlight,
    async_setup_integration,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_setup_retry(menuai: menuai) -> None:
    """Test setup is retried on error."""
    bulb = _mocked_wizlight(None, None, FAKE_SOCKET)
    bulb.getMac = AsyncMock(side_effect=OSError)
    _, entry = await async_setup_integration(menuai, wizlight=bulb)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    bulb.getMac = AsyncMock(return_value=FAKE_MAC)

    with _patch_discovery(), _patch_wizlight(device=bulb):
        await menuai.async_block_till_done(wait_background_tasks=True)
        async_fire_time_changed(menuai, utcnow() + datetime.timedelta(minutes=15))
        await menuai.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def test_cleanup_on_shutdown(menuai: menuai) -> None:
    """Test the socket is cleaned up on shutdown."""
    bulb = _mocked_wizlight(None, None, FAKE_SOCKET)
    _, entry = await async_setup_integration(menuai, wizlight=bulb)
    assert entry.state is ConfigEntryState.LOADED
    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done(wait_background_tasks=True)
    bulb.async_close.assert_called_once()


async def test_cleanup_on_failed_first_update(menuai: menuai) -> None:
    """Test the socket is cleaned up on failed first update."""
    bulb = _mocked_wizlight(None, None, FAKE_SOCKET)
    bulb.updateState = AsyncMock(side_effect=OSError)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=FAKE_MAC,
        data={CONF_HOST: FAKE_IP},
    )
    entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.wiz.discovery.find_wizlights", return_value=[]),
        _patch_wizlight(device=bulb),
    ):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    bulb.async_close.assert_called_once()


async def test_wrong_device_now_has_our_ip(menuai: menuai) -> None:
    """Test setup is retried when the wrong device is found."""
    bulb = _mocked_wizlight(None, None, FAKE_SOCKET)
    bulb.mac = "dddddddddddd"
    _, entry = await async_setup_integration(menuai, wizlight=bulb)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_reload_on_title_change(menuai: menuai) -> None:
    """Test the integration gets reloaded when the title is updated."""
    bulb = _mocked_wizlight(None, None, FAKE_SOCKET)
    _, entry = await async_setup_integration(menuai, wizlight=bulb)
    assert entry.state is ConfigEntryState.LOADED
    await menuai.async_block_till_done(wait_background_tasks=True)

    with _patch_discovery(), _patch_wizlight(device=bulb):
        menuai.config_entries.async_update_entry(entry, title="Shop Switch")
        assert entry.title == "Shop Switch"
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert (
        menuai.states.get("switch.mock_title").attributes[ATTR_FRIENDLY_NAME]
        == "Shop Switch"
    )
