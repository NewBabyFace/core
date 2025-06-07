"""Test the Kodi config flow."""

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from menuai import config_entries
from menuai.components.kodi.config_flow import (
    CannotConnectError,
    InvalidAuthError,
)
from menuai.components.kodi.const import DEFAULT_TIMEOUT, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .util import (
    TEST_CREDENTIALS,
    TEST_DISCOVERY,
    TEST_DISCOVERY_WO_UUID,
    TEST_HOST,
    TEST_IMPORT,
    TEST_WS_PORT,
    UUID,
    MockConnection,
    MockWSConnection,
    get_kodi_connection,
)

from tests.common import MockConfigEntry


@pytest.fixture
async def user_flow(menuai: menuai) -> str:
    """Return a user-initiated flow after filling in host info."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    return result["flow_id"]


async def test_user_flow(menuai: menuai, user_flow: str) -> None:
    """Test a successful user initiated flow."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
        patch(
            "menuai.components.kodi.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_HOST["host"]
    assert result["data"] == {
        **TEST_HOST,
        **TEST_WS_PORT,
        "password": None,
        "username": None,
        "name": None,
        "timeout": DEFAULT_TIMEOUT,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_valid_auth(menuai: menuai, user_flow: str) -> None:
    """Test we handle valid auth."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=InvalidAuthError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
        patch(
            "menuai.components.kodi.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_CREDENTIALS
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_HOST["host"]
    assert result["data"] == {
        **TEST_HOST,
        **TEST_WS_PORT,
        **TEST_CREDENTIALS,
        "name": None,
        "timeout": DEFAULT_TIMEOUT,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_valid_ws_port(menuai: menuai, user_flow: str) -> None:
    """Test we handle valid websocket port."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
        patch(
            "menuai.components.kodi.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_WS_PORT
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_HOST["host"]
    assert result["data"] == {
        **TEST_HOST,
        **TEST_WS_PORT,
        "password": None,
        "username": None,
        "name": None,
        "timeout": DEFAULT_TIMEOUT,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_empty_ws_port(menuai: menuai, user_flow: str) -> None:
    """Test we handle an empty websocket port input."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}

    with patch(
        "menuai.components.kodi.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"ws_port": 0}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_HOST["host"]
    assert result["data"] == {
        **TEST_HOST,
        "ws_port": None,
        "password": None,
        "username": None,
        "name": None,
        "timeout": DEFAULT_TIMEOUT,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai, user_flow: str) -> None:
    """Test we handle invalid auth."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=InvalidAuthError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=InvalidAuthError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_CREDENTIALS
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "invalid_auth"}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=CannotConnectError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_CREDENTIALS
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=Exception,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_CREDENTIALS
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "unknown"}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_CREDENTIALS
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}


async def test_form_cannot_connect_http(menuai: menuai, user_flow: str) -> None:
    """Test we handle cannot connect over HTTP error."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=CannotConnectError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_exception_http(menuai: menuai, user_flow: str) -> None:
    """Test we handle generic exception over HTTP."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=Exception,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_form_cannot_connect_ws(menuai: menuai, user_flow: str) -> None:
    """Test we handle cannot connect over WebSocket error."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection, "connected", new_callable=PropertyMock(return_value=False)
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_WS_PORT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=CannotConnectError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_WS_PORT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_exception_ws(menuai: menuai, user_flow: str) -> None:
    """Test we handle generic exception over WebSocket."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(user_flow, TEST_HOST)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(MockWSConnection, "connect", AsyncMock(side_effect=Exception)),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_WS_PORT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {"base": "unknown"}


async def test_discovery(menuai: menuai) -> None:
    """Test discovery flow works."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    with patch(
        "menuai.components.kodi.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"], user_input={}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "hostname"
    assert result["data"] == {
        **TEST_HOST,
        **TEST_WS_PORT,
        "password": None,
        "username": None,
        "name": "hostname",
        "timeout": DEFAULT_TIMEOUT,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_discovery_cannot_connect_http(menuai: menuai) -> None:
    """Test discovery aborts if cannot connect."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=CannotConnectError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_discovery_cannot_connect_ws(menuai: menuai) -> None:
    """Test discovery aborts if cannot connect to websocket."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch.object(
            MockWSConnection,
            "connect",
            AsyncMock(side_effect=CannotConnectError),
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            new=get_kodi_connection,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ws_port"
    assert result["errors"] == {}


async def test_discovery_exception_http(menuai: menuai) -> None:
    """Test we handle generic exception during discovery validation."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=Exception,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_discovery_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth during discovery."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=InvalidAuthError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {}


async def test_discovery_duplicate_data(menuai: menuai) -> None:
    """Test discovery aborts if same mDNS packet arrives."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=TEST_DISCOVERY,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=TEST_DISCOVERY
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_discovery_updates_unique_id(menuai: menuai) -> None:
    """Test a duplicate discovery id aborts and updates existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UUID,
        data={"host": "dummy", "port": 11, "namename": "dummy.local."},
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=TEST_DISCOVERY
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    assert entry.data["host"] == "1.1.1.1"
    assert entry.data["port"] == 8080
    assert entry.data["name"] == "hostname"


async def test_discovery_without_unique_id(menuai: menuai) -> None:
    """Test a discovery flow with no unique id aborts."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_WO_UUID,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_uuid"


async def test_form_import(menuai: menuai) -> None:
    """Test we get the form with import source."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            return_value=True,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
        patch(
            "menuai.components.kodi.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=TEST_IMPORT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_IMPORT["name"]
    assert result["data"] == TEST_IMPORT

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_import_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth on import."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=InvalidAuthError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=TEST_IMPORT,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_auth"


async def test_form_import_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect on import."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=CannotConnectError,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=TEST_IMPORT,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_form_import_exception(menuai: menuai) -> None:
    """Test we handle unknown exception on import."""
    with (
        patch(
            "menuai.components.kodi.config_flow.Kodi.ping",
            side_effect=Exception,
        ),
        patch(
            "menuai.components.kodi.config_flow.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=TEST_IMPORT,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"
