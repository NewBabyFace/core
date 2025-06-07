"""Test AfterShip config flow."""

from unittest.mock import AsyncMock, patch

from pyaftership import AfterShipException

from menuai.components.aftership.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_full_user_flow(menuai: menuai, mock_setup_entry) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "menuai.components.aftership.config_flow.AfterShip",
        return_value=AsyncMock(),
    ) as mock_aftership:
        mock_aftership.return_value.trackings.return_value.list.return_value = {}
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "mock-api-key",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "AfterShip"
        assert result["data"] == {
            CONF_API_KEY: "mock-api-key",
        }


async def test_flow_cannot_connect(menuai: menuai, mock_setup_entry) -> None:
    """Test handling invalid connection."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch(
        "menuai.components.aftership.config_flow.AfterShip",
        return_value=AsyncMock(),
    ) as mock_aftership:
        mock_aftership.side_effect = AfterShipException
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "mock-api-key",
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

    with patch(
        "menuai.components.aftership.config_flow.AfterShip",
        return_value=AsyncMock(),
    ) as mock_aftership:
        mock_aftership.return_value.trackings.return_value.list.return_value = {}
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "mock-api-key",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "AfterShip"
        assert result["data"] == {
            CONF_API_KEY: "mock-api-key",
        }
