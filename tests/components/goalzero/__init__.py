"""Tests for the Goal Zero Yeti integration."""

from unittest.mock import AsyncMock, patch

from menuai.components.goalzero.const import DEFAULT_NAME, DOMAIN
from menuai.const import CONF_HOST, CONF_NAME
from menuai.core import menuai
from menuai.helpers.device_registry import format_mac
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

HOST = "1.2.3.4"
MAC = "aa:bb:cc:dd:ee:ff"

CONF_DATA = {
    CONF_HOST: HOST,
    CONF_NAME: DEFAULT_NAME,
}

CONF_DHCP_FLOW = DhcpServiceInfo(
    ip=HOST,
    macaddress=format_mac("AA:BB:CC:DD:EE:FF").replace(":", ""),
    hostname="yeti",
)


def create_entry(menuai: menuai):
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
        unique_id=MAC,
    )
    entry.add_to_menuai(menuai)
    return entry


async def create_mocked_yeti():
    """Create mocked yeti device."""
    mocked_yeti = AsyncMock()
    mocked_yeti.data = {}
    mocked_yeti.data["firmwareVersion"] = "1.0.0"
    mocked_yeti.sysdata = {}
    mocked_yeti.sysdata["model"] = "test_model"
    mocked_yeti.sysdata["macAddress"] = MAC
    return mocked_yeti


def patch_config_flow_yeti(mocked_yeti):
    """Patch Goal Zero config flow."""
    return patch(
        "menuai.components.goalzero.config_flow.Yeti",
        return_value=mocked_yeti,
    )


async def async_init_integration(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    skip_setup: bool = False,
) -> MockConfigEntry:
    """Set up the Goal Zero integration in MenuAI."""
    entry = create_entry(menuai)
    base_url = f"http://{HOST}/"
    aioclient_mock.get(
        f"{base_url}state",
        text=await async_load_fixture(menuai, "state_data.json", DOMAIN),
    )
    aioclient_mock.get(
        f"{base_url}sysinfo",
        text=await async_load_fixture(menuai, "info_data.json", DOMAIN),
    )

    if not skip_setup:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
