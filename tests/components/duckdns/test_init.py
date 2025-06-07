"""Test the DuckDNS component."""

from datetime import timedelta
import logging

import pytest

from menuai.components import duckdns
from menuai.components.duckdns import async_track_time_interval_backoff
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker

DOMAIN = "bla"
TOKEN = "abcdefgh"
_LOGGER = logging.getLogger(__name__)
INTERVAL = duckdns.INTERVAL


async def async_set_txt(menuai: menuai, txt: str | None) -> None:
    """Set the txt record. Pass in None to remove it.

    This is a legacy helper method. Do not use it for new tests.
    """
    await menuai.services.async_call(
        duckdns.DOMAIN, duckdns.SERVICE_SET_TXT, {duckdns.ATTR_TXT: txt}, blocking=True
    )


@pytest.fixture
async def setup_duckdns(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Fixture that sets up DuckDNS."""
    aioclient_mock.get(
        duckdns.UPDATE_URL, params={"domains": DOMAIN, "token": TOKEN}, text="OK"
    )

    await async_setup_component(
        menuai, duckdns.DOMAIN, {"duckdns": {"domain": DOMAIN, "access_token": TOKEN}}
    )


async def test_setup(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Test setup works if update passes."""
    aioclient_mock.get(
        duckdns.UPDATE_URL, params={"domains": DOMAIN, "token": TOKEN}, text="OK"
    )

    result = await async_setup_component(
        menuai, duckdns.DOMAIN, {"duckdns": {"domain": DOMAIN, "access_token": TOKEN}}
    )

    await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count == 1

    async_fire_time_changed(menuai, utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 2


async def test_setup_backoff(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup fails if first update fails."""
    aioclient_mock.get(
        duckdns.UPDATE_URL, params={"domains": DOMAIN, "token": TOKEN}, text="KO"
    )

    result = await async_setup_component(
        menuai, duckdns.DOMAIN, {"duckdns": {"domain": DOMAIN, "access_token": TOKEN}}
    )
    assert result
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 1

    # Copy of the DuckDNS intervals from duckdns/__init__.py
    intervals = (
        INTERVAL,
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(minutes=30),
    )
    tme = utcnow()
    await menuai.async_block_till_done()

    _LOGGER.debug("Backoff")
    for idx in range(1, len(intervals)):
        tme += intervals[idx]
        async_fire_time_changed(menuai, tme)
        await menuai.async_block_till_done()

        assert aioclient_mock.call_count == idx + 1


async def test_service_set_txt(
    menuai: menuai, aioclient_mock: AiohttpClientMocker, setup_duckdns
) -> None:
    """Test set txt service call."""
    # Empty the fixture mock requests
    aioclient_mock.clear_requests()

    aioclient_mock.get(
        duckdns.UPDATE_URL,
        params={"domains": DOMAIN, "token": TOKEN, "txt": "some-txt"},
        text="OK",
    )

    assert aioclient_mock.call_count == 0
    await async_set_txt(menuai, "some-txt")
    assert aioclient_mock.call_count == 1


async def test_service_clear_txt(
    menuai: menuai, aioclient_mock: AiohttpClientMocker, setup_duckdns
) -> None:
    """Test clear txt service call."""
    # Empty the fixture mock requests
    aioclient_mock.clear_requests()

    aioclient_mock.get(
        duckdns.UPDATE_URL,
        params={"domains": DOMAIN, "token": TOKEN, "txt": "", "clear": "true"},
        text="OK",
    )

    assert aioclient_mock.call_count == 0
    await async_set_txt(menuai, None)
    assert aioclient_mock.call_count == 1


async def test_async_track_time_interval_backoff(menuai: menuai) -> None:
    """Test setup fails if first update fails."""
    ret_val = False
    call_count = 0
    tme = None

    async def _return(now):
        nonlocal call_count, ret_val, tme
        if tme is None:
            tme = now
        call_count += 1
        return ret_val

    intervals = (
        INTERVAL,
        INTERVAL * 2,
        INTERVAL * 5,
        INTERVAL * 9,
        INTERVAL * 10,
        INTERVAL * 11,
        INTERVAL * 12,
    )

    async_track_time_interval_backoff(menuai, _return, intervals)
    await menuai.async_block_till_done()

    assert call_count == 1

    _LOGGER.debug("Backoff")
    for idx in range(1, len(intervals)):
        tme += intervals[idx]
        async_fire_time_changed(menuai, tme + timedelta(seconds=0.1))
        await menuai.async_block_till_done()

        assert call_count == idx + 1

    _LOGGER.debug("Max backoff reached - intervals[-1]")
    for _idx in range(1, 10):
        tme += intervals[-1]
        async_fire_time_changed(menuai, tme + timedelta(seconds=0.1))
        await menuai.async_block_till_done()

        assert call_count == idx + 1 + _idx

    _LOGGER.debug("Reset backoff")
    call_count = 0
    ret_val = True
    tme += intervals[-1]
    async_fire_time_changed(menuai, tme + timedelta(seconds=0.1))
    await menuai.async_block_till_done()
    assert call_count == 1

    _LOGGER.debug("No backoff - intervals[0]")
    for _idx in range(2, 10):
        tme += intervals[0]
        async_fire_time_changed(menuai, tme + timedelta(seconds=0.1))
        await menuai.async_block_till_done()

        assert call_count == _idx
