"""Test EDL21 config flow."""

import pytest

from menuai.components.edl21.const import CONF_SERIAL_PORT, DEFAULT_TITLE, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

VALID_CONFIG = {CONF_SERIAL_PORT: "/dev/ttyUSB1"}
VALID_LEGACY_CONFIG = {CONF_NAME: "My Smart Meter", CONF_SERIAL_PORT: "/dev/ttyUSB1"}

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"][CONF_SERIAL_PORT] == VALID_CONFIG[CONF_SERIAL_PORT]


async def test_integration_already_exists(menuai: menuai) -> None:
    """Test that a new entry must not have the same serial port as an existing entry."""

    MockConfigEntry(
        domain=DOMAIN,
        data=VALID_CONFIG,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
