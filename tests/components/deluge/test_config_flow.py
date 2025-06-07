"""Test Deluge config flow."""

from unittest.mock import patch

import pytest

from menuai.components.deluge.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import CONF_DATA

from tests.common import MockConfigEntry


@pytest.fixture(name="api")
def mock_deluge_api():
    """Mock an api."""
    with (
        patch("deluge_client.client.DelugeRPCClient.connect"),
        patch("deluge_client.client.DelugeRPCClient._create_socket"),
    ):
        yield


@pytest.fixture(name="conn_error")
def mock_api_connection_error():
    """Mock an api."""
    with (
        patch(
            "deluge_client.client.DelugeRPCClient.connect",
            side_effect=ConnectionRefusedError("111: Connection refused"),
        ),
        patch("deluge_client.client.DelugeRPCClient._create_socket"),
    ):
        yield


@pytest.fixture(name="unknown_error")
def mock_api_unknown_error():
    """Mock an api."""
    with (
        patch("deluge_client.client.DelugeRPCClient.connect", side_effect=Exception),
        patch("deluge_client.client.DelugeRPCClient._create_socket"),
    ):
        yield


@pytest.fixture(name="deluge_setup", autouse=True)
def deluge_setup_fixture():
    """Mock deluge entry setup."""
    with patch("menuai.components.deluge.async_setup_entry", return_value=True):
        yield


async def test_flow_user(menuai: menuai, api) -> None:
    """Test user initialized flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=CONF_DATA,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"] == CONF_DATA


async def test_flow_user_already_configured(menuai: menuai, api) -> None:
    """Test user initialized flow with duplicate server."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=CONF_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_user_cannot_connect(menuai: menuai, conn_error) -> None:
    """Test user initialized flow with unreachable server."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=CONF_DATA
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_unknown_error(menuai: menuai, unknown_error) -> None:
    """Test user initialized flow with unreachable server."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=CONF_DATA
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_flow_reauth(menuai: menuai, api) -> None:
    """Test reauth step."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONF_DATA,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == CONF_DATA
