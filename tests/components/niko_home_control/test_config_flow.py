"""Test niko_home_control config flow."""

from unittest.mock import AsyncMock, patch

from menuai.components.niko_home_control.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai,
    mock_niko_home_control_connection: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.123"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Niko Home Control"
    assert result["data"] == {CONF_HOST: "192.168.0.123"}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_cannot_connect(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test the cannot connect error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.niko_home_control.config_flow.NHCController.connect",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.0.123"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(
        "menuai.components.niko_home_control.config_flow.NHCController.connect",
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.0.123"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_entry(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test uniqueness."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.123"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
