"""Tests for the LCN config flow."""

from unittest.mock import patch

from pypck.connection import (
    PchkAuthenticationError,
    PchkConnectionFailedError,
    PchkConnectionRefusedError,
    PchkLicenseError,
)
import pytest

from menuai import config_entries, data_entry_flow
from menuai.components.lcn.config_flow import LcnFlowHandler, validate_connection
from menuai.components.lcn.const import (
    CONF_ACKNOWLEDGE,
    CONF_DIM_MODE,
    CONF_SK_NUM_TRIES,
    DOMAIN,
)
from menuai.const import (
    CONF_BASE,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from menuai.core import menuai

from tests.common import MockConfigEntry

CONFIG_DATA = {
    CONF_IP_ADDRESS: "127.0.0.1",
    CONF_PORT: 1234,
    CONF_USERNAME: "lcn",
    CONF_PASSWORD: "lcn",
    CONF_SK_NUM_TRIES: 0,
    CONF_DIM_MODE: "STEPS200",
    CONF_ACKNOWLEDGE: False,
}

CONNECTION_DATA = {CONF_HOST: "pchk", **CONFIG_DATA}

IMPORT_DATA = {
    **CONNECTION_DATA,
    CONF_DEVICES: [],
    CONF_ENTITIES: [],
}


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    flow = LcnFlowHandler()
    flow.menuai = menuai

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user(menuai: menuai) -> None:
    """Test for user step."""
    with (
        patch("menuai.components.lcn.PchkConnectionManager.async_connect"),
        patch("menuai.components.lcn.async_setup_entry", return_value=True),
    ):
        data = CONNECTION_DATA.copy()
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == CONNECTION_DATA[CONF_HOST]
        assert result["data"] == {
            **CONNECTION_DATA,
            CONF_DEVICES: [],
            CONF_ENTITIES: [],
        }


async def test_step_user_existing_host(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test for user defined host already exists."""
    entry.add_to_menuai(menuai)

    with patch("menuai.components.lcn.PchkConnectionManager.async_connect"):
        config_data = entry.data.copy()
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_data
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("error", "errors"),
    [
        (PchkAuthenticationError, {CONF_BASE: "authentication_error"}),
        (PchkLicenseError, {CONF_BASE: "license_error"}),
        (PchkConnectionFailedError, {CONF_BASE: "connection_refused"}),
        (PchkConnectionRefusedError, {CONF_BASE: "connection_refused"}),
    ],
)
async def test_step_user_error(
    menuai: menuai, error: type[Exception], errors: dict[str, str]
) -> None:
    """Test for error in user step is handled correctly."""
    with patch(
        "menuai.components.lcn.PchkConnectionManager.async_connect",
        side_effect=error,
    ):
        data = CONNECTION_DATA.copy()
        data.update({CONF_HOST: "pchk"})
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == errors


async def test_step_reconfigure(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test for reconfigure step."""
    entry.add_to_menuai(menuai)
    old_entry_data = entry.data.copy()

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        patch("menuai.components.lcn.PchkConnectionManager.async_connect"),
        patch("menuai.components.lcn.async_setup_entry", return_value=True),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_DATA.copy(),
        )
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"

        entry = menuai.config_entries.async_get_entry(entry.entry_id)
        assert entry.title == CONNECTION_DATA[CONF_HOST]
        assert entry.data == {**old_entry_data, **CONFIG_DATA}


@pytest.mark.parametrize(
    ("error", "errors"),
    [
        (PchkAuthenticationError, {CONF_BASE: "authentication_error"}),
        (PchkLicenseError, {CONF_BASE: "license_error"}),
        (PchkConnectionFailedError, {CONF_BASE: "connection_refused"}),
        (PchkConnectionRefusedError, {CONF_BASE: "connection_refused"}),
    ],
)
async def test_step_reconfigure_error(
    menuai: menuai,
    entry: MockConfigEntry,
    error: type[Exception],
    errors: dict[str, str],
) -> None:
    """Test for error in reconfigure step is handled correctly."""
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "menuai.components.lcn.PchkConnectionManager.async_connect",
        side_effect=error,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_DATA.copy(),
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == errors


async def test_validate_connection() -> None:
    """Test the connection validation."""
    data = CONNECTION_DATA.copy()

    with (
        patch(
            "menuai.components.lcn.PchkConnectionManager.async_connect"
        ) as async_connect,
        patch(
            "menuai.components.lcn.PchkConnectionManager.async_close"
        ) as async_close,
    ):
        result = await validate_connection(data=data)

    assert async_connect.is_called
    assert async_close.is_called
    assert result is None
