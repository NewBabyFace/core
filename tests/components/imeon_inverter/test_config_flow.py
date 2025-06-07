"""Test the Imeon Inverter config flow."""

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from menuai.components.imeon_inverter.const import DOMAIN
from menuai.config_entries import SOURCE_SSDP, SOURCE_USER
from menuai.const import CONF_HOST, CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import ATTR_UPNP_SERIAL

from .conftest import TEST_DISCOVER, TEST_SERIAL, TEST_USER_INPUT

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_async_setup_entry")


async def test_form_valid(
    menuai: menuai,
    mock_async_setup_entry: AsyncMock,
) -> None:
    """Test we get the form and the config is created with the good entries."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Imeon {TEST_SERIAL}"
    assert result["data"] == TEST_USER_INPUT
    assert result["result"].unique_id == TEST_SERIAL
    assert mock_async_setup_entry.call_count == 1


async def test_form_invalid_auth(
    menuai: menuai, mock_imeon_inverter: MagicMock
) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    mock_imeon_inverter.login.return_value = False

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_imeon_inverter.login.return_value = True

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError, "cannot_connect"),
        (ValueError("Host invalid"), "invalid_host"),
        (ValueError("Route invalid"), "invalid_route"),
        (ValueError, "unknown"),
    ],
)
async def test_form_exception(
    menuai: menuai,
    mock_imeon_inverter: MagicMock,
    error: Exception,
    expected: str,
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    mock_imeon_inverter.login.side_effect = error

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}

    mock_imeon_inverter.login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_manual_setup_already_exists(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that a flow with an existing id aborts."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_get_serial_timeout(
    menuai: menuai, mock_imeon_inverter: MagicMock
) -> None:
    """Test the timeout error handling of getting the serial number."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    mock_imeon_inverter.get_serial.side_effect = TimeoutError

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_imeon_inverter.get_serial.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_ssdp(menuai: menuai) -> None:
    """Test a ssdp discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=TEST_DISCOVER,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = TEST_USER_INPUT.copy()
    user_input.pop(CONF_HOST)

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Imeon {TEST_SERIAL}"
    assert result["data"] == TEST_USER_INPUT


async def test_ssdp_already_exist(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that a ssdp discovery flow with an existing id aborts."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=TEST_DISCOVER,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ssdp_abort(menuai: menuai) -> None:
    """Test that a ssdp discovery aborts if serial is unknown."""
    data = deepcopy(TEST_DISCOVER)
    data.upnp.pop(ATTR_UPNP_SERIAL, None)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=data,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
