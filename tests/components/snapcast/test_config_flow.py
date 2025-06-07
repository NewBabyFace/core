"""Test the Snapcast module."""

import socket
from unittest.mock import AsyncMock, patch

import pytest

from menuai import config_entries, setup
from menuai.components.snapcast.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_CONNECTION = {CONF_HOST: "snapserver.test", CONF_PORT: 1705}

pytestmark = pytest.mark.usefixtures("mock_setup_entry", "mock_create_server")


async def test_form(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_create_server: AsyncMock
) -> None:
    """Test we get the form and handle errors and successful connection."""
    await setup.async_setup_component(menuai, "persistent_notification", {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    # test invalid host error
    with patch("snapcast.control.create_server", side_effect=socket.gaierror):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONNECTION,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_host"}

    # test connection error
    with patch("snapcast.control.create_server", side_effect=ConnectionRefusedError):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONNECTION,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # test success
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_CONNECTION
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Snapcast"
    assert result["data"] == {CONF_HOST: "snapserver.test", CONF_PORT: 1705}
    assert len(mock_create_server.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_abort(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_create_server: AsyncMock
) -> None:
    """Test config flow abort if device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONNECTION,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with patch("snapcast.control.create_server", side_effect=socket.gaierror):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONNECTION,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
