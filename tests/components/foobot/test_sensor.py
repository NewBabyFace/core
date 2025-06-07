"""The tests for the Foobot sensor platform."""

from http import HTTPStatus
import re
from unittest.mock import MagicMock

import pytest

from menuai.components import sensor
from menuai.components.foobot import sensor as foobot
from menuai.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.exceptions import PlatformNotReady
from menuai.setup import async_setup_component

from tests.common import async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

VALID_CONFIG = {
    "platform": "foobot",
    "token": "adfdsfasd",
    "username": "example@example.com",
}


async def test_default_setup(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the default setup."""
    aioclient_mock.get(
        re.compile("api.foobot.io/v2/owner/.*"),
        text=await async_load_fixture(menuai, "devices.json", "foobot"),
    )
    aioclient_mock.get(
        re.compile("api.foobot.io/v2/device/.*"),
        text=await async_load_fixture(menuai, "data.json", "foobot"),
    )
    assert await async_setup_component(menuai, sensor.DOMAIN, {"sensor": VALID_CONFIG})
    await menuai.async_block_till_done()

    metrics = {
        "co2": ["1232.0", CONCENTRATION_PARTS_PER_MILLION],
        "temperature": ["21.1", UnitOfTemperature.CELSIUS],
        "humidity": ["49.5", PERCENTAGE],
        "pm2_5": ["144.8", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
        "voc": ["340.7", CONCENTRATION_PARTS_PER_BILLION],
        "index": ["138.9", PERCENTAGE],
    }

    for name, value in metrics.items():
        state = menuai.states.get(f"sensor.foobot_happybot_{name}")
        assert state.state == value[0]
        assert state.attributes.get("unit_of_measurement") == value[1]


async def test_setup_timeout_error(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Expected failures caused by a timeout in API response."""
    fake_async_add_entities = MagicMock()

    aioclient_mock.get(re.compile("api.foobot.io/v2/owner/.*"), exc=TimeoutError())
    with pytest.raises(PlatformNotReady):
        await foobot.async_setup_platform(menuai, VALID_CONFIG, fake_async_add_entities)


async def test_setup_permanent_error(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Expected failures caused by permanent errors in API response."""
    fake_async_add_entities = MagicMock()

    errors = [HTTPStatus.BAD_REQUEST, HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]
    for error in errors:
        aioclient_mock.get(re.compile("api.foobot.io/v2/owner/.*"), status=error)
        result = await foobot.async_setup_platform(
            menuai, VALID_CONFIG, fake_async_add_entities
        )
        assert result is None


async def test_setup_temporary_error(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Expected failures caused by temporary errors in API response."""
    fake_async_add_entities = MagicMock()

    errors = [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.INTERNAL_SERVER_ERROR]
    for error in errors:
        aioclient_mock.get(re.compile("api.foobot.io/v2/owner/.*"), status=error)
        with pytest.raises(PlatformNotReady):
            await foobot.async_setup_platform(
                menuai, VALID_CONFIG, fake_async_add_entities
            )
