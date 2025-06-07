"""Test the devolo Home Network config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from devolo_plc_api.exceptions.device import DeviceNotFound, DevicePasswordProtected
import pytest

from menuai import config_entries
from menuai.components.devolo_home_network.const import (
    DOMAIN,
    SERIAL_NUMBER,
    TITLE,
)
from menuai.const import CONF_BASE, CONF_IP_ADDRESS, CONF_NAME, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import configure_integration
from .const import (
    DISCOVERY_INFO,
    DISCOVERY_INFO_CHANGED,
    DISCOVERY_INFO_WRONG_DEVICE,
    IP,
    IP_ALT,
)
from .mock import MockDevice, MockDeviceWrongPassword


async def test_form(menuai: menuai, info: dict[str, Any]) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.devolo_home_network.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_IP_ADDRESS: IP, CONF_PASSWORD: ""},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["result"].unique_id == info[SERIAL_NUMBER]
    assert result2["title"] == info[TITLE]
    assert result2["data"] == {
        CONF_IP_ADDRESS: IP,
        CONF_PASSWORD: "",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception_type", "expected_error"),
    [
        (DeviceNotFound(IP), "cannot_connect"),
        (DevicePasswordProtected, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_form_error(menuai: menuai, exception_type, expected_error) -> None:
    """Test we handle errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.devolo_home_network.config_flow.validate_input",
        side_effect=exception_type,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_IP_ADDRESS: IP, CONF_PASSWORD: ""},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_BASE: expected_error}

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDevice,
        ),
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_IP_ADDRESS: IP, CONF_PASSWORD: ""},
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_zeroconf(menuai: menuai) -> None:
    """Test that the zeroconf form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO,
    )

    assert result["step_id"] == "zeroconf_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {"host_name": "test"}

    context = next(
        flow["context"]
        for flow in menuai.config_entries.flow.async_progress()
        if flow["flow_id"] == result["flow_id"]
    )

    assert (
        context["title_placeholders"][CONF_NAME]
        == DISCOVERY_INFO.hostname.split(".", maxsplit=1)[0]
    )

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDevice,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["title"] == "test"
    assert result2["data"] == {
        CONF_IP_ADDRESS: IP,
        CONF_PASSWORD: "",
    }
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["result"].unique_id == "1234567890"


async def test_zeroconf_wrong_auth(menuai: menuai) -> None:
    """Test that the zeroconf form asks for password if authorization fails."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO,
    )

    assert result["step_id"] == "zeroconf_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {"host_name": "test"}

    context = next(
        flow["context"]
        for flow in menuai.config_entries.flow.async_progress()
        if flow["flow_id"] == result["flow_id"]
    )

    assert (
        context["title_placeholders"][CONF_NAME]
        == DISCOVERY_INFO.hostname.split(".", maxsplit=1)[0]
    )

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDeviceWrongPassword,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_BASE: "invalid_auth"}

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDevice,
        ),
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_PASSWORD: "new-password",
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_abort_zeroconf_wrong_device(menuai: menuai) -> None:
    """Test we abort zeroconf for wrong devices."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO_WRONG_DEVICE,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "home_control"


@pytest.mark.usefixtures("info")
async def test_abort_if_configured(menuai: menuai) -> None:
    """Test we abort config flow if already configured."""
    entry = configure_integration(menuai)

    # Abort on concurrent user flow
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IP_ADDRESS: IP,
        },
    )
    await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"

    # Abort on concurrent zeroconf discovery flow
    result3 = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO_CHANGED,
    )
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_configured"
    assert entry.data[CONF_IP_ADDRESS] == IP_ALT


@pytest.mark.usefixtures("mock_device")
@pytest.mark.usefixtures("mock_zeroconf")
async def test_form_reauth(menuai: menuai) -> None:
    """Test that the reauth confirmation form is served."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDeviceWrongPassword,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-wrong-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_BASE: "invalid_auth"}

    with (
        patch(
            "menuai.components.devolo_home_network.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.devolo_home_network.config_flow.Device",
            new=MockDevice,
        ),
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-right-password"},
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1
    assert entry.data[CONF_PASSWORD] == "test-right-password"
