"""The tests for the litejet component."""

from unittest.mock import patch

from serial import SerialException

from menuai import config_entries
from menuai.components.litejet.const import CONF_DEFAULT_TRANSITION, DOMAIN
from menuai.const import CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_show_config_form(menuai: menuai) -> None:
    """Test show configuration form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_create_entry(menuai: menuai, mock_litejet) -> None:
    """Test create entry from user input."""
    test_data = {CONF_PORT: "/dev/test"}

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=test_data
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "/dev/test"
    assert result["data"] == test_data


async def test_flow_entry_already_exists(menuai: menuai) -> None:
    """Test user input when a config entry already exists."""
    first_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PORT: "/dev/first"},
    )
    first_entry.add_to_menuai(menuai)

    test_data = {CONF_PORT: "/dev/test"}

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=test_data
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_flow_open_failed(menuai: menuai) -> None:
    """Test user input when serial port open fails."""
    test_data = {CONF_PORT: "/dev/test"}

    with patch("pylitejet.LiteJet") as mock_pylitejet:
        mock_pylitejet.side_effect = SerialException

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=test_data
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_PORT] == "open_failed"


async def test_options(menuai: menuai) -> None:
    """Test updating options."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PORT: "/dev/test"})
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_DEFAULT_TRANSITION: 12},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_DEFAULT_TRANSITION: 12}
