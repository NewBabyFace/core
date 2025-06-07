"""Configure pytest for Skybell tests."""

from unittest.mock import AsyncMock, patch

from aioskybell import Skybell, SkybellDevice
from aioskybell.helpers.const import BASE_URL, USERS_ME_URL
import orjson
import pytest

from menuai.components.skybell.const import DOMAIN
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

USERNAME = "user"
PASSWORD = "password"
USER_ID = "1234567890abcdef12345678"
DEVICE_ID = "012345670123456789abcdef"

CONF_DATA = {
    CONF_EMAIL: USERNAME,
    CONF_PASSWORD: PASSWORD,
}


@pytest.fixture(autouse=True)
def skybell_mock():
    """Fixture for our skybell tests."""
    mocked_skybell_device = AsyncMock(spec=SkybellDevice)

    mocked_skybell = AsyncMock(spec=Skybell)
    mocked_skybell.async_get_devices.return_value = [mocked_skybell_device]
    mocked_skybell.async_send_request.return_value = {"id": USER_ID}
    mocked_skybell.user_id = USER_ID

    with (
        patch(
            "menuai.components.skybell.config_flow.Skybell",
            return_value=mocked_skybell,
        ),
        patch("menuai.components.skybell.Skybell", return_value=mocked_skybell),
    ):
        yield mocked_skybell


def create_entry(menuai: menuai) -> MockConfigEntry:
    """Create fixture for adding config entry in MenuAI."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=USER_ID, data=CONF_DATA)
    entry.add_to_menuai(menuai)
    return entry


async def set_aioclient_responses(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Set AioClient responses."""
    aioclient_mock.get(
        f"{BASE_URL}devices/{DEVICE_ID}/info/",
        text=await async_load_fixture(menuai, "device_info.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{BASE_URL}devices/{DEVICE_ID}/settings/",
        text=await async_load_fixture(menuai, "device_settings.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{BASE_URL}devices/{DEVICE_ID}/activities/",
        text=await async_load_fixture(menuai, "activities.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{BASE_URL}devices/",
        text=await async_load_fixture(menuai, "device.json", DOMAIN),
    )
    aioclient_mock.get(
        USERS_ME_URL,
        text=await async_load_fixture(menuai, "me.json", DOMAIN),
    )
    aioclient_mock.post(
        f"{BASE_URL}login/",
        text=await async_load_fixture(menuai, "login.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{BASE_URL}devices/{DEVICE_ID}/activities/1234567890ab1234567890ac/video/",
        text=await async_load_fixture(menuai, "video.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{BASE_URL}devices/{DEVICE_ID}/avatar/",
        text=await async_load_fixture(menuai, "avatar.json", DOMAIN),
    )
    aioclient_mock.get(
        f"https://v3-production-devices-avatar.s3.us-west-2.amazonaws.com/{DEVICE_ID}.jpg",
    )
    aioclient_mock.get(
        f"https://skybell-thumbnails-stage.s3.amazonaws.com/{DEVICE_ID}/1646859244793-951{DEVICE_ID}_{DEVICE_ID}.jpeg",
    )


@pytest.fixture
async def connection(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Fixture for good connection responses."""
    await set_aioclient_responses(menuai, aioclient_mock)


async def create_skybell(menuai: menuai) -> Skybell:
    """Create Skybell object."""
    skybell = Skybell(
        username=USERNAME,
        password=PASSWORD,
        get_devices=True,
        session=async_get_clientsession(menuai),
    )
    skybell._cache = orjson.loads(await async_load_fixture(menuai, "cache.json", DOMAIN))
    return skybell


async def mock_skybell(menuai: menuai):
    """Mock Skybell object."""
    return patch(
        "menuai.components.skybell.Skybell",
        return_value=await create_skybell(menuai),
    )


async def async_init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the Skybell integration in MenuAI."""
    config_entry = create_entry(menuai)

    with await mock_skybell(menuai), patch("aioskybell.utils.async_save_cache"):
        await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    return config_entry
