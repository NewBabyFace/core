"""Define tests for the israel rail config flow."""

from unittest.mock import AsyncMock

from menuai.components.israel_rail import CONF_DESTINATION, CONF_START, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import VALID_CONFIG

from tests.common import MockConfigEntry


async def test_create_entry(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_israelrail: AsyncMock
) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_CONFIG,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "באר יעקב אשקלון"
    assert result["data"] == {
        CONF_START: "באר יעקב",
        CONF_DESTINATION: "אשקלון",
    }


async def test_flow_fails(
    menuai: menuai,
    mock_israelrail: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that the user step fails."""
    mock_israelrail.query.side_effect = Exception("error")
    failed_result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert failed_result["errors"] == {"base": "unknown"}
    assert failed_result["type"] is FlowResultType.FORM

    mock_israelrail.query.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        failed_result["flow_id"],
        VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "באר יעקב אשקלון"
    assert result["data"] == {
        CONF_START: "באר יעקב",
        CONF_DESTINATION: "אשקלון",
    }


async def test_flow_already_configured(
    menuai: menuai,
    mock_israelrail: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that the user step fails when the entry is already configured."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result_aborted = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_CONFIG,
    )

    assert result_aborted["type"] is FlowResultType.ABORT
    assert result_aborted["reason"] == "already_configured"
