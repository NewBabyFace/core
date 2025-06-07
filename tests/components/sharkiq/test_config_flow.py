"""Test the Shark IQ config flow."""

from unittest.mock import patch

import aiohttp
import pytest
from sharkiq import AylaApi, SharkIqAuthError, SharkIqError

from menuai import config_entries
from menuai.components.sharkiq.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component

from .const import (
    CONFIG,
    CONFIG_NO_REGION,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_USERNAME,
    UNIQUE_ID,
)

from tests.common import MockConfigEntry


async def test_setup_success_no_region(menuai: menuai) -> None:
    """Test reauth flow."""
    mock_config = MockConfigEntry(
        domain=DOMAIN, unique_id=UNIQUE_ID, data=CONFIG_NO_REGION
    )
    mock_config.add_to_menuai(menuai)

    result = await async_setup_component(menuai=menuai, domain=DOMAIN, config={})

    assert result is True


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch("sharkiq.AylaApi.async_sign_in", return_value=True),
        patch(
            "menuai.components.sharkiq.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == f"{TEST_USERNAME:s}"
    assert result2["data"] == {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "region": TEST_REGION,
    }

    await menuai.async_block_till_done()
    mock_setup_entry.assert_called_once()


@pytest.mark.parametrize(
    ("exc", "base_error"),
    [
        (SharkIqAuthError, "invalid_auth"),
        (aiohttp.ClientError, "cannot_connect"),
        (TypeError, "cannot_connect"),
        (SharkIqError, "unknown"),
    ],
)
async def test_form_error(menuai: menuai, exc: Exception, base_error: str) -> None:
    """Test form errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch.object(AylaApi, "async_sign_in", side_effect=exc):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"].get("base") == base_error


async def test_reauth_success(menuai: menuai) -> None:
    """Test reauth flow."""
    mock_config = MockConfigEntry(domain=DOMAIN, unique_id=UNIQUE_ID, data=CONFIG)
    mock_config.add_to_menuai(menuai)

    result = await mock_config.start_reauth_flow(menuai)

    with patch("sharkiq.AylaApi.async_sign_in", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=CONFIG
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("side_effect", "result_type", "msg_field", "msg"),
    [
        (SharkIqAuthError, "form", "errors", "invalid_auth"),
        (aiohttp.ClientError, "abort", "reason", "cannot_connect"),
        (TypeError, "abort", "reason", "cannot_connect"),
        (SharkIqError, "abort", "reason", "unknown"),
    ],
)
async def test_reauth(
    menuai: menuai,
    side_effect: Exception,
    result_type: str,
    msg_field: str,
    msg: str,
) -> None:
    """Test reauth failures."""
    mock_config = MockConfigEntry(domain=DOMAIN, unique_id=UNIQUE_ID, data=CONFIG)
    mock_config.add_to_menuai(menuai)

    result = await mock_config.start_reauth_flow(menuai)

    with patch("sharkiq.AylaApi.async_sign_in", side_effect=side_effect):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=CONFIG
        )
        msg_value = result[msg_field]
        if msg_field == "errors":
            msg_value = msg_value.get("base")

        assert result["type"] == result_type
        assert msg_value == msg
