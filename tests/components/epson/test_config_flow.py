"""Test the epson config flow."""

from unittest.mock import patch

from epson_projector.const import PWR_OFF_STATE

from menuai import config_entries
from menuai.components.epson.const import CONF_CONNECTION_TYPE, DOMAIN, HTTP
from menuai.const import CONF_HOST, CONF_NAME, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    with patch("menuai.components.epson.Projector.get_power", return_value="01"):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == config_entries.SOURCE_USER
    with (
        patch(
            "menuai.components.epson.Projector.get_power",
            return_value="01",
        ),
        patch(
            "menuai.components.epson.Projector.get_serial_number",
            return_value="12345",
        ),
        patch(
            "menuai.components.epson.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.epson.Projector.close",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_NAME: "test-epson"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-epson"
    assert result2["data"] == {CONF_CONNECTION_TYPE: HTTP, CONF_HOST: "1.1.1.1"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.epson.Projector.get_power",
        return_value=STATE_UNAVAILABLE,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_NAME: "test-epson"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_powered_off(menuai: menuai) -> None:
    """Test we handle powered off during initial configuration."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.epson.Projector.get_power",
        return_value=PWR_OFF_STATE,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_NAME: "test-epson"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "powered_off"}
