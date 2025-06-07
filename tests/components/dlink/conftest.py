"""Configure pytest for D-Link tests."""

from collections.abc import Awaitable, Callable, Generator
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.dlink.const import CONF_USE_LEGACY_PROTOCOL, DOMAIN
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.helpers.device_registry import format_mac
from menuai.helpers.service_info.dhcp import DhcpServiceInfo
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

HOST = "1.2.3.4"
PASSWORD = "123456"
MAC = format_mac("AA:BB:CC:DD:EE:FF")
DHCP_FORMATTED_MAC = MAC.replace(":", "")
USERNAME = "admin"

CONF_DHCP_DATA = {
    CONF_USERNAME: USERNAME,
    CONF_PASSWORD: PASSWORD,
    CONF_USE_LEGACY_PROTOCOL: True,
}

CONF_DATA = CONF_DHCP_DATA | {CONF_HOST: HOST}

CONF_DHCP_FLOW = DhcpServiceInfo(
    ip=HOST,
    macaddress=DHCP_FORMATTED_MAC,
    hostname="dsp-w215",
)

CONF_DHCP_FLOW_NEW_IP = DhcpServiceInfo(
    ip="5.6.7.8",
    macaddress=DHCP_FORMATTED_MAC,
    hostname="dsp-w215",
)

type ComponentSetup = Callable[[], Awaitable[None]]


def create_entry(menuai: menuai, unique_id: str | None = None) -> MockConfigEntry:
    """Create fixture for adding config entry in MenuAI."""
    entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA, unique_id=unique_id)
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Add config entry in MenuAI."""
    return create_entry(menuai)


@pytest.fixture
def config_entry_with_uid(menuai: menuai) -> MockConfigEntry:
    """Add config entry with unique ID in MenuAI."""
    return create_entry(menuai, unique_id="aabbccddeeff")


@pytest.fixture
def mocked_plug() -> MagicMock:
    """Create mocked plug device."""
    mocked_plug = MagicMock()
    mocked_plug.state = "OFF"
    mocked_plug.temperature = "33"
    mocked_plug.current_consumption = "50"
    mocked_plug.total_consumption = "1040"
    mocked_plug.authenticated = None
    mocked_plug.use_legacy_protocol = False
    mocked_plug.model_name = "DSP-W215"
    return mocked_plug


@pytest.fixture
def mocked_plug_legacy() -> MagicMock:
    """Create mocked legacy plug device."""
    mocked_plug = MagicMock()
    mocked_plug.state = "OFF"
    mocked_plug.temperature = "N/A"
    mocked_plug.current_consumption = "N/A"
    mocked_plug.total_consumption = "N/A"
    mocked_plug.authenticated = ("0123456789ABCDEF0123456789ABCDEF", "ABCDefGHiJ")
    mocked_plug.use_legacy_protocol = True
    mocked_plug.model_name = "DSP-W215"
    return mocked_plug


@pytest.fixture
def mocked_plug_legacy_no_auth(mocked_plug_legacy: MagicMock) -> MagicMock:
    """Create mocked legacy unauthenticated plug device."""
    mocked_plug_legacy = deepcopy(mocked_plug_legacy)
    mocked_plug_legacy.authenticated = None
    return mocked_plug_legacy


def patch_config_flow(mocked_plug: MagicMock):
    """Patch D-Link Smart Plug config flow."""
    return patch(
        "menuai.components.dlink.config_flow.SmartPlug",
        return_value=mocked_plug,
    )


def patch_setup(mocked_plug: MagicMock):
    """Patch D-Link Smart Plug object."""
    return patch(
        "menuai.components.dlink.SmartPlug",
        return_value=mocked_plug,
    )


async def mock_setup_integration(
    menuai: menuai,
    mocked_plug: MagicMock,
) -> None:
    """Set up the D-Link integration in MenuAI."""
    with patch_setup(mocked_plug):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()


@pytest.fixture
async def setup_integration(
    menuai: menuai,
    config_entry_with_uid: MockConfigEntry,
    mocked_plug: MagicMock,
) -> Generator[ComponentSetup]:
    """Set up the D-Link integration in MenuAI."""

    async def func() -> None:
        await mock_setup_integration(menuai, mocked_plug)

    return func


@pytest.fixture
async def setup_integration_legacy(
    menuai: menuai,
    config_entry_with_uid: MockConfigEntry,
    mocked_plug_legacy: MagicMock,
) -> Generator[ComponentSetup]:
    """Set up the D-Link integration in MenuAI with different data."""

    async def func() -> None:
        await mock_setup_integration(menuai, mocked_plug_legacy)

    return func
