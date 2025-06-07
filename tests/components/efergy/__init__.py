"""Tests for Efergy integration."""

from unittest.mock import AsyncMock, patch

from pyefergy import exceptions

from menuai.components.efergy.const import DOMAIN
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

TOKEN = "9p6QGJ7dpZfO3fqPTBk1fyEmjV1cGoLT"
MULTI_SENSOR_TOKEN = "9r6QGF7dpZfO3fqPTBl1fyRmjV1cGoLT"

CONF_DATA = {CONF_API_KEY: TOKEN}
HID = "12345678901234567890123456789012"

BASE_URL = "https://engage.efergy.com/mobile_proxy/"


def create_entry(menuai: menuai, token: str = TOKEN) -> MockConfigEntry:
    """Create Efergy entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=HID,
        data={CONF_API_KEY: token},
    )
    entry.add_to_menuai(menuai)
    return entry


async def init_integration(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    token: str = TOKEN,
    error: bool = False,
) -> MockConfigEntry:
    """Set up the Efergy integration in MenuAI."""
    entry = create_entry(menuai, token=token)
    await mock_responses(menuai, aioclient_mock, token=token, error=error)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry


async def mock_responses(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    token: str = TOKEN,
    error: bool = False,
):
    """Mock responses from Efergy."""
    base_url = "https://engage.efergy.com/mobile_proxy/"
    if error:
        aioclient_mock.get(
            f"{base_url}getInstant?token={token}",
            exc=exceptions.ConnectError,
        )
        return
    aioclient_mock.get(
        f"{base_url}getStatus?token={token}",
        text=await async_load_fixture(menuai, "status.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getInstant?token={token}",
        text=await async_load_fixture(menuai, "instant.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getEnergy?period=day",
        text=await async_load_fixture(menuai, "daily_energy.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getEnergy?period=week",
        text=await async_load_fixture(menuai, "weekly_energy.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getEnergy?period=month",
        text=await async_load_fixture(menuai, "monthly_energy.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getEnergy?period=year",
        text=await async_load_fixture(menuai, "yearly_energy.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getBudget?token={token}",
        text=await async_load_fixture(menuai, "budget.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getCost?period=day",
        text=await async_load_fixture(menuai, "daily_cost.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getCost?period=week",
        text=await async_load_fixture(menuai, "weekly_cost.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getCost?period=month",
        text=await async_load_fixture(menuai, "monthly_cost.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}getCost?period=year",
        text=await async_load_fixture(menuai, "yearly_cost.json", DOMAIN),
    )
    if token == TOKEN:
        aioclient_mock.get(
            f"{base_url}getCurrentValuesSummary?token={token}",
            text=await async_load_fixture(menuai, "current_values_single.json", DOMAIN),
        )
    else:
        aioclient_mock.get(
            f"{base_url}getCurrentValuesSummary?token={token}",
            text=await async_load_fixture(menuai, "current_values_multi.json", DOMAIN),
        )


def _patch_efergy():
    mocked_efergy = AsyncMock()
    mocked_efergy.info = {}
    mocked_efergy.info["hid"] = HID
    mocked_efergy.info["mac"] = "AA:BB:CC:DD:EE:FF"
    mocked_efergy.info["status"] = "on"
    mocked_efergy.info["type"] = "EEEHub"
    mocked_efergy.info["version"] = "2.3.7"
    return patch(
        "menuai.components.efergy.config_flow.Efergy",
        return_value=mocked_efergy,
    )


def _patch_efergy_status():
    return patch("menuai.components.efergy.config_flow.Efergy.async_status")


async def setup_platform(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    platform: str,
    token: str = TOKEN,
    error: bool = False,
):
    """Set up the platform."""
    entry = await init_integration(menuai, aioclient_mock, token=token, error=error)

    with patch("menuai.components.efergy.PLATFORMS", [platform]):
        assert await async_setup_component(menuai, DOMAIN, {})

    return entry
