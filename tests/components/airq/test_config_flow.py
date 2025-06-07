"""Test the air-Q config flow."""

import logging
from unittest.mock import patch

from aioairq import DeviceInfo, InvalidAuth
from aiohttp.client_exceptions import ClientConnectionError
import pytest

from menuai import config_entries
from menuai.components.airq.const import (
    CONF_CLIP_NEGATIVE,
    CONF_RETURN_AVERAGE,
    DOMAIN,
)
from menuai.const import CONF_IP_ADDRESS, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

TEST_USER_DATA = {
    CONF_IP_ADDRESS: "192.168.0.0",
    CONF_PASSWORD: "password",
}
TEST_DEVICE_INFO = DeviceInfo(
    id="id",
    name="name",
    model="model",
    sw_version="sw",
    hw_version="hw",
)
DEFAULT_OPTIONS = {
    CONF_CLIP_NEGATIVE: True,
    CONF_RETURN_AVERAGE: True,
}


async def test_form(menuai: menuai, caplog: pytest.LogCaptureFixture) -> None:
    """Test we get the form."""
    caplog.set_level(logging.DEBUG)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch("aioairq.AirQ.validate"),
        patch("aioairq.AirQ.fetch_device_info", return_value=TEST_DEVICE_INFO),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_USER_DATA,
        )
        await menuai.async_block_till_done()
        assert f"Creating an entry for {TEST_DEVICE_INFO['name']}" in caplog.text

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_DEVICE_INFO["name"]
    assert result2["data"] == TEST_USER_DATA


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("aioairq.AirQ.validate", side_effect=InvalidAuth):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_DATA | {CONF_PASSWORD: "wrong_password"}
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("aioairq.AirQ.validate", side_effect=ClientConnectionError):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_DATA
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_duplicate_error(menuai: menuai) -> None:
    """Test that errors are shown when duplicates are added."""
    MockConfigEntry(
        data=TEST_USER_DATA,
        domain=DOMAIN,
        unique_id=TEST_DEVICE_INFO["id"],
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("aioairq.AirQ.validate"),
        patch("aioairq.AirQ.fetch_device_info", return_value=TEST_DEVICE_INFO),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_DATA
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.parametrize(
    "user_input", [{}, {CONF_RETURN_AVERAGE: False}, {CONF_CLIP_NEGATIVE: False}]
)
async def test_options_flow(menuai: menuai, user_input) -> None:
    """Test that the options flow works."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=TEST_USER_DATA, unique_id=TEST_DEVICE_INFO["id"]
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert entry.options == {}

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == entry.options == DEFAULT_OPTIONS | user_input
