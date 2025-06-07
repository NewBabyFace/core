"""Test the SlimProto Player config flow."""

from unittest.mock import AsyncMock

from menuai.components.slimproto.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == DEFAULT_NAME
    assert result.get("data") == {}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test abort if SlimProto Player is already configured."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"
