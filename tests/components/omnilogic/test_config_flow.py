"""Test the Omnilogic config flow."""

from unittest.mock import patch

from omnilogic import LoginException, OmniLogicException

from menuai import config_entries
from menuai.components.omnilogic.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

DATA = {"username": "test-username", "password": "test-password"}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.omnilogic.config_flow.OmniLogic.connect",
            return_value=True,
        ),
        patch(
            "menuai.components.omnilogic.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Omnilogic"
    assert result2["data"] == DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(menuai: menuai) -> None:
    """Test config flow when Omnilogic component is already setup."""
    MockConfigEntry(domain="omnilogic", data=DATA).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_with_invalid_credentials(menuai: menuai) -> None:
    """Test with invalid credentials."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.omnilogic.OmniLogic.connect",
        side_effect=LoginException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test if invalid response or no connection returned from Hayward."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.omnilogic.OmniLogic.connect",
        side_effect=OmniLogicException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_with_unknown_error(menuai: menuai) -> None:
    """Test with unknown error response from Hayward."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.omnilogic.OmniLogic.connect",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_option_flow(menuai: menuai) -> None:
    """Test option flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_menuai(menuai)

    assert not entry.options

    with patch(
        "menuai.components.omnilogic.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.options.async_init(
            entry.entry_id,
            data=None,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"polling_interval": 9},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"]["polling_interval"] == 9
