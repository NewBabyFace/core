"""Test the NO-IP component."""

from datetime import timedelta

import pytest

from menuai.components import no_ip
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker

DOMAIN = "test.example.com"

PASSWORD = "xyz789"

UPDATE_URL = no_ip.UPDATE_URL

USERNAME = "abc@123.com"


@pytest.fixture
async def setup_no_ip(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Fixture that sets up NO-IP."""
    aioclient_mock.get(UPDATE_URL, params={"hostname": DOMAIN}, text="good 0.0.0.0")

    await async_setup_component(
        menuai,
        no_ip.DOMAIN,
        {
            no_ip.DOMAIN: {
                "domain": DOMAIN,
                "username": USERNAME,
                "password": PASSWORD,
            }
        },
    )


async def test_setup(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Test setup works if update passes."""
    aioclient_mock.get(UPDATE_URL, params={"hostname": DOMAIN}, text="nochg 0.0.0.0")

    result = await async_setup_component(
        menuai,
        no_ip.DOMAIN,
        {no_ip.DOMAIN: {"domain": DOMAIN, "username": USERNAME, "password": PASSWORD}},
    )
    assert result
    assert aioclient_mock.call_count == 1

    async_fire_time_changed(menuai, utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 2


async def test_setup_fails_if_update_fails(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup fails if first update fails."""
    aioclient_mock.get(UPDATE_URL, params={"hostname": DOMAIN}, text="nohost")

    result = await async_setup_component(
        menuai,
        no_ip.DOMAIN,
        {no_ip.DOMAIN: {"domain": DOMAIN, "username": USERNAME, "password": PASSWORD}},
    )
    assert not result
    assert aioclient_mock.call_count == 1


async def test_setup_fails_if_wrong_auth(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup fails if first update fails through wrong authentication."""
    aioclient_mock.get(UPDATE_URL, params={"hostname": DOMAIN}, text="badauth")

    result = await async_setup_component(
        menuai,
        no_ip.DOMAIN,
        {no_ip.DOMAIN: {"domain": DOMAIN, "username": USERNAME, "password": PASSWORD}},
    )
    assert not result
    assert aioclient_mock.call_count == 1
