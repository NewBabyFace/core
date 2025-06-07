"""Test the V2C config flow."""

from unittest.mock import AsyncMock

import pytest
from pytrydan.exceptions import TrydanError

from menuai.components.v2c.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_full_flow(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_v2c_client: AsyncMock
) -> None:
    """Test we can finish a config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "1.1.1.1"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "EVSE 1.1.1.1"
    assert result["data"] == {CONF_HOST: "1.1.1.1"}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (TrydanError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_form_cannot_connect(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    side_effect: Exception,
    error: str,
    mock_v2c_client: AsyncMock,
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    mock_v2c_client.get_data.side_effect = side_effect
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "1.1.1.1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    mock_v2c_client.get_data.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "1.1.1.1"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "EVSE 1.1.1.1"
    assert result["data"] == {CONF_HOST: "1.1.1.1"}
