"""Test the ProgettiHWSW Automation config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.progettihwsw.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

mock_value_step_user = {
    "title": "1R & 1IN Board",
    "relay_count": 1,
    "input_count": 1,
    "is_old": False,
}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_value_step_rm = {
        "relay_1": "bistable",  # Mocking a single relay board instance.
    }

    with patch(
        "menuai.components.progettihwsw.config_flow.ProgettiHWSWAPI.check_board",
        return_value=mock_value_step_user,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "", CONF_PORT: 80},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "relay_modes"
    assert result2["errors"] == {}

    with patch(
        "menuai.components.progettihwsw.async_setup_entry",
        return_value=True,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            mock_value_step_rm,
        )

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"]
    assert result3["data"]["title"] == "1R & 1IN Board"
    assert result3["data"]["is_old"] is False
    assert result3["data"]["relay_count"] == result3["data"]["input_count"] == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle unexisting board."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["step_id"] == "user"

    with patch(
        "menuai.components.progettihwsw.config_flow.ProgettiHWSWAPI.check_board",
        return_value=False,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "", CONF_PORT: 80},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_existing_entry_exception(menuai: menuai) -> None:
    """Test we handle existing board."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["step_id"] == "user"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "",
            CONF_PORT: 80,
        },
    )
    entry.add_to_menuai(menuai)

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "", CONF_PORT: 80},
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_form_user_exception(menuai: menuai) -> None:
    """Test we handle unknown exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["step_id"] == "user"

    with patch(
        "menuai.components.progettihwsw.config_flow.validate_input",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "", CONF_PORT: 80},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "unknown"}
