"""Test the Arve config flow."""

from unittest.mock import AsyncMock

from menuai.components.arve.config_flow import ArveConnectionError
from menuai.components.arve.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ACCESS_TOKEN, CONF_CLIENT_SECRET
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import USER_INPUT, async_init_integration

from tests.common import MockConfigEntry


async def test_correct_flow(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_arve: AsyncMock
) -> None:
    """Test the whole flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == USER_INPUT
    assert len(mock_setup_entry.mock_calls) == 1
    assert result2["result"].unique_id == 12345


async def test_form_cannot_connect(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_arve: AsyncMock
) -> None:
    """Test we handle cannot connect error."""
    mock_arve.get_customer_id.side_effect = ArveConnectionError
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_abort_already_configured(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test form aborts if already configured."""
    await async_init_integration(menuai, mock_config_entry)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ACCESS_TOKEN: "test-access-token",
            CONF_CLIENT_SECRET: "test-customer-token",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
