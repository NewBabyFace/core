"""Tests for the Netgear config flow."""

from unittest.mock import Mock, patch

from pynetgear import DEFAULT_USER
import pytest

from menuai.components.netgear.const import (
    CONF_CONSIDER_HOME,
    DOMAIN,
    MODELS_PORT_5555,
    PORT_80,
    PORT_5555,
)
from menuai.config_entries import SOURCE_SSDP, SOURCE_USER
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_MODEL_NUMBER,
    ATTR_UPNP_PRESENTATION_URL,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)

from tests.common import MockConfigEntry

URL = "http://routerlogin.net"
URL_SSL = "https://routerlogin.net"
SERIAL = "5ER1AL0000001"

ROUTER_INFOS = {
    "Description": "Netgear Smart Wizard 3.0, specification 1.6 version",
    "SignalStrength": "-4",
    "SmartAgentversion": "3.0",
    "FirewallVersion": "net-wall 2.0",
    "VPNVersion": None,
    "OthersoftwareVersion": "N/A",
    "Hardwareversion": "N/A",
    "Otherhardwareversion": "N/A",
    "FirstUseDate": "Sunday, 30 Sep 2007 01:10:03",
    "DeviceMode": "0",
    "ModelName": "RBR20",
    "SerialNumber": SERIAL,
    "Firmwareversion": "V2.3.5.26",
    "DeviceName": "Desk",
    "DeviceNameUserSet": "true",
    "FirmwareDLmethod": "HTTPS",
    "FirmwareLastUpdate": "2019_10.5_18:42:58",
    "FirmwareLastChecked": "2020_5.3_1:33:0",
    "DeviceModeCapability": "0;1",
}
TITLE = f"{ROUTER_INFOS['ModelName']} - {ROUTER_INFOS['DeviceName']}"
TITLE_INCOMPLETE = ROUTER_INFOS["ModelName"]

HOST = "10.0.0.1"
SERIAL_2 = "5ER1AL0000002"
PORT = 80
SSL = False
USERNAME = "Home_Assistant"
PASSWORD = "password"
SSDP_URL = f"http://{HOST}:{PORT}/rootDesc.xml"
SSDP_URLipv6 = f"http://[::ffff:a00:1]:{PORT}/rootDesc.xml"
SSDP_URL_SLL = f"https://{HOST}:{PORT}/rootDesc.xml"


@pytest.fixture(name="service")
def mock_controller_service():
    """Mock a successful service."""
    with (
        patch("menuai.components.netgear.async_setup_entry", return_value=True),
        patch("menuai.components.netgear.router.Netgear") as service_mock,
    ):
        service_mock.return_value.get_info = Mock(return_value=ROUTER_INFOS)
        service_mock.return_value.port = 80
        service_mock.return_value.ssl = False
        yield service_mock


async def test_user(menuai: menuai, service) -> None:
    """Test user step."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Have to provide all config
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == TITLE
    assert result["data"].get(CONF_HOST) == HOST
    assert result["data"].get(CONF_PORT) == PORT
    assert result["data"].get(CONF_SSL) == SSL
    assert result["data"].get(CONF_USERNAME) == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_user_connect_error(menuai: menuai, service) -> None:
    """Test user step with connection failure."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    service.return_value.get_info = Mock(return_value=None)

    # Have to provide all config
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "info"}

    service.return_value.login_try_port = Mock(return_value=None)

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "config"}


async def test_user_incomplete_info(menuai: menuai, service) -> None:
    """Test user step with incomplete device info."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    router_infos = ROUTER_INFOS.copy()
    router_infos.pop("DeviceName")
    service.return_value.get_info = Mock(return_value=router_infos)

    # Have to provide all config
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == TITLE_INCOMPLETE
    assert result["data"].get(CONF_HOST) == HOST
    assert result["data"].get(CONF_PORT) == PORT
    assert result["data"].get(CONF_SSL) == SSL
    assert result["data"].get(CONF_USERNAME) == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_abort_if_already_setup(menuai: menuai, service) -> None:
    """Test we abort if the router is already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PASSWORD: PASSWORD},
        unique_id=SERIAL,
    ).add_to_menuai(menuai)

    # Should fail, same SERIAL (flow)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ssdp_already_configured(menuai: menuai) -> None:
    """Test ssdp abort when the router is already configured."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PASSWORD: PASSWORD},
        unique_id=SERIAL,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=SSDP_URL_SLL,
            upnp={
                ATTR_UPNP_MODEL_NUMBER: "RBR20",
                ATTR_UPNP_PRESENTATION_URL: URL,
                ATTR_UPNP_SERIAL: SERIAL,
            },
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ssdp_no_serial(menuai: menuai) -> None:
    """Test ssdp abort when the ssdp info does not include a serial number."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=SSDP_URL,
            upnp={
                ATTR_UPNP_MODEL_NUMBER: "RBR20",
                ATTR_UPNP_PRESENTATION_URL: URL,
            },
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_serial"


async def test_ssdp_ipv6(menuai: menuai) -> None:
    """Test ssdp abort when using a ipv6 address."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PASSWORD: PASSWORD},
        unique_id=SERIAL,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=SSDP_URLipv6,
            upnp={
                ATTR_UPNP_MODEL_NUMBER: "RBR20",
                ATTR_UPNP_PRESENTATION_URL: URL,
                ATTR_UPNP_SERIAL: SERIAL,
            },
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_ipv4_address"


async def test_ssdp(menuai: menuai, service) -> None:
    """Test ssdp step."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=SSDP_URL,
            upnp={
                ATTR_UPNP_MODEL_NUMBER: "RBR20",
                ATTR_UPNP_PRESENTATION_URL: URL,
                ATTR_UPNP_SERIAL: SERIAL,
            },
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == TITLE
    assert result["data"].get(CONF_HOST) == HOST
    assert result["data"].get(CONF_PORT) == PORT_80
    assert result["data"].get(CONF_SSL) == SSL
    assert result["data"].get(CONF_USERNAME) == DEFAULT_USER
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_ssdp_port_5555(menuai: menuai, service) -> None:
    """Test ssdp step with port 5555."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=SSDP_URL_SLL,
            upnp={
                ATTR_UPNP_MODEL_NUMBER: MODELS_PORT_5555[0],
                ATTR_UPNP_PRESENTATION_URL: URL_SSL,
                ATTR_UPNP_SERIAL: SERIAL,
            },
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    service.return_value.port = 5555
    service.return_value.ssl = True

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == TITLE
    assert result["data"].get(CONF_HOST) == HOST
    assert result["data"].get(CONF_PORT) == PORT_5555
    assert result["data"].get(CONF_SSL) is True
    assert result["data"].get(CONF_USERNAME) == DEFAULT_USER
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_options_flow(menuai: menuai, service) -> None:
    """Test specifying non default settings using options flow."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PASSWORD: PASSWORD},
        unique_id=SERIAL,
        title=TITLE,
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONSIDER_HOME: 1800,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_CONSIDER_HOME: 1800,
    }
