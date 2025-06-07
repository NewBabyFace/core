"""Test the smarty config flow."""

from unittest.mock import AsyncMock

from menuai.components.smarty.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai, mock_smarty: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test the full flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.0.2"
    assert result["data"] == {CONF_HOST: "192.168.0.2"}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_cannot_connect(
    menuai: menuai, mock_smarty: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle cannot connect error."""

    mock_smarty.update.return_value = False

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_smarty.update.return_value = True

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_unknown_error(
    menuai: menuai, mock_smarty: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle unknown error."""

    mock_smarty.update.side_effect = Exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}

    mock_smarty.update.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_existing_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test we handle existing entry."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.2"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
