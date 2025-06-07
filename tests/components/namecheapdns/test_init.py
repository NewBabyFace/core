"""Test the NamecheapDNS component."""

from datetime import timedelta

import pytest

from menuai.components import namecheapdns
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker

HOST = "test"
DOMAIN = "bla"
PASSWORD = "abcdefgh"


@pytest.fixture
async def setup_namecheapdns(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Fixture that sets up NamecheapDNS."""
    aioclient_mock.get(
        namecheapdns.UPDATE_URL,
        params={"host": HOST, "domain": DOMAIN, "password": PASSWORD},
        text="<interface-response><ErrCount>0</ErrCount></interface-response>",
    )

    await async_setup_component(
        menuai,
        namecheapdns.DOMAIN,
        {"namecheapdns": {"host": HOST, "domain": DOMAIN, "password": PASSWORD}},
    )


async def test_setup(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Test setup works if update passes."""
    aioclient_mock.get(
        namecheapdns.UPDATE_URL,
        params={"host": HOST, "domain": DOMAIN, "password": PASSWORD},
        text="<interface-response><ErrCount>0</ErrCount></interface-response>",
    )

    result = await async_setup_component(
        menuai,
        namecheapdns.DOMAIN,
        {"namecheapdns": {"host": HOST, "domain": DOMAIN, "password": PASSWORD}},
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
    aioclient_mock.get(
        namecheapdns.UPDATE_URL,
        params={"host": HOST, "domain": DOMAIN, "password": PASSWORD},
        text="<interface-response><ErrCount>1</ErrCount></interface-response>",
    )

    result = await async_setup_component(
        menuai,
        namecheapdns.DOMAIN,
        {"namecheapdns": {"host": HOST, "domain": DOMAIN, "password": PASSWORD}},
    )
    assert not result
    assert aioclient_mock.call_count == 1
