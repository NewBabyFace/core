"""Tests for the Cert Expiry config flow."""

import socket
import ssl
from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.cert_expiry.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import HOST, PORT

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user(menuai: menuai) -> None:
    """Test user config."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.cert_expiry.config_flow.get_cert_expiry_timestamp"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: HOST, CONF_PORT: PORT}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == PORT
    assert result["result"].unique_id == f"{HOST}:{PORT}"


async def test_user_with_bad_cert(menuai: menuai) -> None:
    """Test user config with bad certificate."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.cert_expiry.helper.async_get_cert",
        side_effect=ssl.SSLError("some error"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: HOST, CONF_PORT: PORT}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == PORT
    assert result["result"].unique_id == f"{HOST}:{PORT}"


async def test_abort_if_already_setup(menuai: menuai) -> None:
    """Test we abort if the cert is already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_HOST: HOST, CONF_PORT: PORT},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_abort_on_socket_failed(menuai: menuai) -> None:
    """Test we abort of we have errors during socket creation."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.cert_expiry.helper.async_get_cert",
        side_effect=socket.gaierror(),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: HOST}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "resolve_failed"}

    with patch(
        "menuai.components.cert_expiry.helper.async_get_cert",
        side_effect=TimeoutError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: HOST}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "connection_timeout"}

    with patch(
        "menuai.components.cert_expiry.helper.async_get_cert",
        side_effect=ConnectionRefusedError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: HOST}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "connection_refused"}
