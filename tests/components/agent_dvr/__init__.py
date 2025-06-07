"""Tests for the agent_dvr component."""

from menuai.components.agent_dvr.const import DOMAIN, SERVER_URL
from menuai.const import CONF_HOST, CONF_PORT, CONTENT_TYPE_JSON
from menuai.core import menuai

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

CONF_DATA = {
    CONF_HOST: "example.local",
    CONF_PORT: 8090,
    SERVER_URL: "http://example.local:8090/",
}


def create_entry(menuai: menuai):
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="c0715bba-c2d0-48ef-9e3e-bc81c9ea4447",
        data=CONF_DATA,
    )
    entry.add_to_menuai(menuai)
    return entry


async def init_integration(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    skip_setup: bool = False,
) -> MockConfigEntry:
    """Set up the Agent DVR integration in MenuAI."""

    aioclient_mock.get(
        "http://example.local:8090/command.cgi?cmd=getStatus",
        text=await async_load_fixture(menuai, "status.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )
    aioclient_mock.get(
        "http://example.local:8090/command.cgi?cmd=getObjects",
        text=await async_load_fixture(menuai, "objects.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )
    entry = create_entry(menuai)

    if not skip_setup:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
