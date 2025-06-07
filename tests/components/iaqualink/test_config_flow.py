"""Tests for iAqualink config flow."""

from unittest.mock import patch

from iaqualink.exception import (
    AqualinkServiceException,
    AqualinkServiceUnauthorizedException,
)

from menuai.components.iaqualink import DOMAIN, config_flow
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_already_configured(
    menuai: menuai, config_entry, config_data
) -> None:
    """Test config flow when iaqualink component is already setup."""
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_without_config(menuai: menuai) -> None:
    """Test config flow with no configuration."""
    flow = config_flow.AqualinkFlowHandler()
    flow.menuai = menuai
    flow.context = {}

    result = await flow.async_step_user()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_with_invalid_credentials(menuai: menuai, config_data) -> None:
    """Test config flow with invalid username and/or password."""
    flow = config_flow.AqualinkFlowHandler()
    flow.menuai = menuai

    with patch(
        "menuai.components.iaqualink.config_flow.AqualinkClient.login",
        side_effect=AqualinkServiceUnauthorizedException,
    ):
        result = await flow.async_step_user(config_data)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_service_exception(menuai: menuai, config_data) -> None:
    """Test config flow encountering service exception."""
    flow = config_flow.AqualinkFlowHandler()
    flow.menuai = menuai

    with patch(
        "menuai.components.iaqualink.config_flow.AqualinkClient.login",
        side_effect=AqualinkServiceException,
    ):
        result = await flow.async_step_user(config_data)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_with_existing_config(menuai: menuai, config_data) -> None:
    """Test config flow with existing configuration."""
    flow = config_flow.AqualinkFlowHandler()
    flow.menuai = menuai
    flow.context = {}

    with patch(
        "menuai.components.iaqualink.config_flow.AqualinkClient.login",
        return_value=None,
    ):
        result = await flow.async_step_user(config_data)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == config_data["username"]
    assert result["data"] == config_data
