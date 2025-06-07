"""Test the Vilfo Router config flow."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from vilfo.exceptions import AuthenticationException, VilfoException

from menuai.components.vilfo.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ACCESS_TOKEN, CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("user_input", "expected_unique_id", "mac"),
    [
        (
            {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
            "testadmin.vilfo.com",
            None,
        ),
        (
            {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
            "FF-00-00-00-00-00",
            "FF-00-00-00-00-00",
        ),
        (
            {CONF_HOST: "192.168.0.1", CONF_ACCESS_TOKEN: "test-token"},
            "FF-00-00-00-00-00",
            "FF-00-00-00-00-00",
        ),
        (
            {CONF_HOST: "2001:db8::1428:57ab", CONF_ACCESS_TOKEN: "test-token"},
            "FF-00-00-00-00-00",
            "FF-00-00-00-00-00",
        ),
    ],
)
async def test_full_flow(
    menuai: menuai,
    mock_vilfo_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_is_valid_host: AsyncMock,
    user_input: dict[str, Any],
    expected_unique_id: str,
    mac: str | None,
) -> None:
    """Test we can finish a config flow."""

    mock_vilfo_client.resolve_mac_address.return_value = mac
    mock_vilfo_client.mac = mac

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == user_input[CONF_HOST]
    assert result["data"] == user_input
    assert result["result"].unique_id == expected_unique_id

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(
    menuai: menuai,
    mock_vilfo_client: AsyncMock,
    mock_is_valid_host: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we handle invalid auth."""
    mock_vilfo_client.get_board_information.side_effect = AuthenticationException
    mock_vilfo_client.resolve_mac_address.return_value = None

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_vilfo_client.get_board_information.side_effect = None
    mock_vilfo_client.resolve_mac_address.return_value = "FF-00-00-00-00-00"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [(VilfoException, "cannot_connect"), (Exception, "unknown")],
)
async def test_form_exceptions(
    menuai: menuai,
    mock_vilfo_client: AsyncMock,
    mock_is_valid_host: AsyncMock,
    mock_setup_entry: AsyncMock,
    side_effect: Exception,
    error: str,
) -> None:
    """Test we handle exceptions."""
    mock_vilfo_client.ping.side_effect = side_effect
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_vilfo_client.ping.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_form_wrong_host(
    menuai: menuai,
    mock_is_valid_host: AsyncMock,
) -> None:
    """Test we handle wrong host errors."""
    mock_is_valid_host.return_value = False
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: "this is an invalid hostname",
            CONF_ACCESS_TOKEN: "test-token",
        },
    )

    assert result["errors"] == {"base": "invalid_host"}


async def test_form_already_configured(
    menuai: menuai,
    mock_vilfo_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mock_is_valid_host: AsyncMock,
) -> None:
    """Test that we handle already configured exceptions appropriately."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "testadmin.vilfo.com", CONF_ACCESS_TOKEN: "test-token"},
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
