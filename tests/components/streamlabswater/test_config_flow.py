"""Test the StreamLabs config flow."""

from unittest.mock import AsyncMock, patch

from menuai import config_entries
from menuai.components.streamlabswater.const import DOMAIN
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch("menuai.components.streamlabswater.config_flow.StreamlabsClient"):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Streamlabs"
    assert result["data"] == {CONF_API_KEY: "abc"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.streamlabswater.config_flow.StreamlabsClient.get_locations",
        return_value={},
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch("menuai.components.streamlabswater.config_flow.StreamlabsClient"):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Streamlabs"
    assert result["data"] == {CONF_API_KEY: "abc"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_unknown(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.streamlabswater.config_flow.StreamlabsClient.get_locations",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}

    with patch("menuai.components.streamlabswater.config_flow.StreamlabsClient"):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Streamlabs"
    assert result["data"] == {CONF_API_KEY: "abc"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_entry_already_exists(menuai: menuai) -> None:
    """Test we handle if the entry already exists."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "abc"},
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.streamlabswater.config_flow.StreamlabsClient.get_locations",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "abc"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
