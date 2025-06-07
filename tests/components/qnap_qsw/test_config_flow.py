"""Define tests for the QNAP QSW config flow."""

from unittest.mock import MagicMock, patch

from aioqsw.const import API_MAC_ADDR, API_PRODUCT, API_RESULT
from aioqsw.exceptions import LoginError, QswError

from menuai import config_entries
from menuai.components.qnap_qsw.const import DOMAIN
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.device_registry import format_mac
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from .util import CONFIG, LIVE_MOCK, SYSTEM_BOARD_MOCK, USERS_LOGIN_MOCK

from tests.common import MockConfigEntry

DHCP_SERVICE_INFO = DhcpServiceInfo(
    hostname="qsw-m408-4c",
    ip="192.168.1.200",
    macaddress="245ebe000000",
)

TEST_PASSWORD = "test-password"
TEST_URL = f"http://{DHCP_SERVICE_INFO.ip}"
TEST_USERNAME = "test-username"


async def test_form(menuai: menuai) -> None:
    """Test that the form is served with valid input."""

    with (
        patch(
            "menuai.components.qnap_qsw.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.get_live",
            return_value=LIVE_MOCK,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.get_system_board",
            return_value=SYSTEM_BOARD_MOCK,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.post_users_login",
            return_value=USERS_LOGIN_MOCK,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

        await menuai.async_block_till_done()

        conf_entries = menuai.config_entries.async_entries(DOMAIN)
        entry = conf_entries[0]
        assert entry.state is ConfigEntryState.LOADED

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert (
            result["title"]
            == f"QNAP {SYSTEM_BOARD_MOCK[API_RESULT][API_PRODUCT]} {SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]}"
        )
        assert result["data"][CONF_URL] == CONFIG[CONF_URL]
        assert result["data"][CONF_USERNAME] == CONFIG[CONF_USERNAME]
        assert result["data"][CONF_PASSWORD] == CONFIG[CONF_PASSWORD]

        assert len(mock_setup_entry.mock_calls) == 1


async def test_form_duplicated_id(menuai: menuai) -> None:
    """Test setting up duplicated entry."""

    system_board = MagicMock()
    system_board.get_mac = MagicMock(
        return_value=SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG,
        unique_id=format_mac(SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]),
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        return_value=system_board,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_form_unique_id_error(menuai: menuai) -> None:
    """Test unique ID error."""

    system_board = MagicMock()
    system_board.get_mac = MagicMock(return_value=None)

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        return_value=system_board,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "invalid_id"


async def test_connection_error(menuai: menuai) -> None:
    """Test connection to host error."""

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        side_effect=QswError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {CONF_URL: "cannot_connect"}


async def test_login_error(menuai: menuai) -> None:
    """Test login error."""

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        side_effect=LoginError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}


async def test_dhcp_flow(menuai: menuai) -> None:
    """Test that DHCP discovery works."""
    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovered_connection"

    with (
        patch(
            "menuai.components.qnap_qsw.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.get_live",
            return_value=LIVE_MOCK,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.get_system_board",
            return_value=SYSTEM_BOARD_MOCK,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.post_users_login",
            return_value=USERS_LOGIN_MOCK,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_URL: TEST_URL,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_dhcp_flow_error(menuai: menuai) -> None:
    """Test that DHCP discovery fails."""

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.get_live",
        side_effect=QswError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_dhcp_connection_error(menuai: menuai) -> None:
    """Test DHCP connection to host error."""

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovered_connection"

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        side_effect=QswError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["errors"] == {"base": "cannot_connect"}


async def test_dhcp_login_error(menuai: menuai) -> None:
    """Test DHCP login error."""

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovered_connection"

    with patch(
        "menuai.components.qnap_qsw.QnapQswApi.validate",
        side_effect=LoginError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}
