"""Test the Mullvad config flow."""

from unittest.mock import patch

from mullvad_api import MullvadAPIError

from menuai import config_entries, setup
from menuai.components.mullvad.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_user(menuai: menuai) -> None:
    """Test we can setup by the user."""
    await setup.async_setup_component(menuai, DOMAIN, {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with (
        patch(
            "menuai.components.mullvad.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.mullvad.config_flow.MullvadAPI"
        ) as mock_mullvad_api,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Mullvad VPN"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_mullvad_api.mock_calls) == 1


async def test_form_user_only_once(menuai: menuai) -> None:
    """Test we can setup by the user only once."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_connection_error(menuai: menuai) -> None:
    """Test we show an error when we have trouble connecting."""
    await setup.async_setup_component(menuai, DOMAIN, {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.mullvad.config_flow.MullvadAPI",
        side_effect=MullvadAPIError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_unknown_error(menuai: menuai) -> None:
    """Test we show an error when an unknown error occurs."""
    await setup.async_setup_component(menuai, DOMAIN, {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.mullvad.config_flow.MullvadAPI",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
