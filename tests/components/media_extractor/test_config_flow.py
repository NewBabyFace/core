"""Tests for the Media extractor config flow."""

from menuai.components.media_extractor.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(menuai: menuai, mock_setup_entry) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Media extractor"
    assert result.get("data") == {}
    assert result.get("options") == {}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_single_instance_allowed(menuai: menuai) -> None:
    """Test we abort if already setup."""
    mock_config_entry = MockConfigEntry(domain=DOMAIN)

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"
