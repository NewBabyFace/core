"""Test the Devialet diagnostics."""

import json

from menuai.components.devialet.const import DOMAIN
from menuai.core import menuai

from . import setup_integration

from tests.common import async_load_fixture
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test diagnostics."""
    entry = await setup_integration(menuai, aioclient_mock)

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == {
        "is_available": True,
        "general_info": json.loads(
            await async_load_fixture(menuai, "general_info.json", DOMAIN)
        ),
        "sources": json.loads(await async_load_fixture(menuai, "sources.json", DOMAIN)),
        "source_state": json.loads(
            await async_load_fixture(menuai, "source_state.json", DOMAIN)
        ),
        "volume": json.loads(await async_load_fixture(menuai, "volume.json", DOMAIN)),
        "night_mode": json.loads(
            await async_load_fixture(menuai, "night_mode.json", DOMAIN)
        ),
        "equalizer": json.loads(
            await async_load_fixture(menuai, "equalizer.json", DOMAIN)
        ),
        "source_list": [
            "Airplay",
            "Bluetooth",
            "Optical left",
            "Optical right",
            "Raat",
            "Spotify Connect",
            "UPnP",
        ],
        "source": "spotifyconnect",
        "upnp_device_type": "Not available",
        "upnp_device_url": "Not available",
    }
