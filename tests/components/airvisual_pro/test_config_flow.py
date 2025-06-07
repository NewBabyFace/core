"""Test the AirVisual Pro config flow."""

from unittest.mock import AsyncMock, patch

from pyairvisual.node import (
    InvalidAuthenticationError,
    NodeConnectionError,
    NodeProError,
)
import pytest

from menuai.components.airvisual_pro.const import DOMAIN
from menuai.config_entries import SOURCE_IMPORT, SOURCE_USER
from menuai.const import CONF_IP_ADDRESS, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.mark.parametrize(
    ("connect_mock", "connect_errors"),
    [
        (AsyncMock(side_effect=Exception), {"base": "unknown"}),
        (AsyncMock(side_effect=InvalidAuthenticationError), {"base": "invalid_auth"}),
        (AsyncMock(side_effect=NodeConnectionError), {"base": "cannot_connect"}),
        (AsyncMock(side_effect=NodeProError), {"base": "unknown"}),
    ],
)
async def test_create_entry(
    menuai: menuai, config, connect_errors, connect_mock, pro, setup_airvisual_pro
) -> None:
    """Test creating an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test errors that can arise when connecting to a Pro:
    with patch.object(pro, "async_connect", connect_mock):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=config
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == connect_errors

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.101"
    assert result["data"] == {
        CONF_IP_ADDRESS: "192.168.1.101",
        CONF_PASSWORD: "password123",
    }


async def test_duplicate_error(
    menuai: menuai, config, config_entry, setup_airvisual_pro
) -> None:
    """Test that errors are shown when duplicates are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_import(menuai: menuai, config, setup_airvisual_pro) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.101"
    assert result["data"] == {
        CONF_IP_ADDRESS: "192.168.1.101",
        CONF_PASSWORD: "password123",
    }


@pytest.mark.parametrize(
    ("connect_mock", "connect_errors"),
    [
        (AsyncMock(side_effect=Exception), {"base": "unknown"}),
        (AsyncMock(side_effect=InvalidAuthenticationError), {"base": "invalid_auth"}),
        (AsyncMock(side_effect=NodeConnectionError), {"base": "cannot_connect"}),
        (AsyncMock(side_effect=NodeProError), {"base": "unknown"}),
    ],
)
async def test_reauth(
    menuai: menuai,
    config,
    config_entry: MockConfigEntry,
    connect_errors,
    connect_mock,
    pro,
    setup_airvisual_pro,
) -> None:
    """Test re-auth (including errors)."""
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # Test errors that can arise when connecting to a Pro:
    with patch.object(pro, "async_connect", connect_mock):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PASSWORD: "new_password"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == connect_errors

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PASSWORD: "new_password"}
    )

    # Allow reload to finish:
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(menuai.config_entries.async_entries()) == 1
