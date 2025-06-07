"""Test the nexia config flow."""

from unittest.mock import MagicMock, patch

import aiohttp
from nexia.const import BRAND_ASAIR, BRAND_NEXIA
import pytest

from menuai import config_entries
from menuai.components.nexia.const import CONF_BRAND, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.mark.parametrize("brand", [BRAND_ASAIR, BRAND_NEXIA])
async def test_form(menuai: menuai, brand) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.nexia.config_flow.NexiaHome.get_name",
            return_value="myhouse",
        ),
        patch(
            "menuai.components.nexia.config_flow.NexiaHome.login",
            side_effect=MagicMock(),
        ),
        patch(
            "menuai.components.nexia.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BRAND: brand, CONF_USERNAME: "username", CONF_PASSWORD: "password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "myhouse"
    assert result2["data"] == {
        CONF_BRAND: brand,
        CONF_USERNAME: "username",
        CONF_PASSWORD: "password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.nexia.config_flow.NexiaHome.login",
        ),
        patch(
            "menuai.components.nexia.config_flow.NexiaHome.get_name",
            return_value=None,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BRAND: BRAND_NEXIA,
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nexia.config_flow.NexiaHome.login",
        side_effect=TimeoutError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BRAND: BRAND_NEXIA,
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_invalid_auth_http_401(menuai: menuai) -> None:
    """Test we handle invalid auth error from http 401."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nexia.config_flow.NexiaHome.login",
        side_effect=aiohttp.ClientResponseError(
            status=401, request_info=MagicMock(), history=MagicMock()
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BRAND: BRAND_NEXIA,
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect_not_found(menuai: menuai) -> None:
    """Test we handle cannot connect from an http not found error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nexia.config_flow.NexiaHome.login",
        side_effect=aiohttp.ClientResponseError(
            status=404, request_info=MagicMock(), history=MagicMock()
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BRAND: BRAND_NEXIA,
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_broad_exception(menuai: menuai) -> None:
    """Test we handle invalid auth error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nexia.config_flow.NexiaHome.login",
        side_effect=ValueError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BRAND: BRAND_NEXIA,
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
