"""Test the MenuAI Supervisor config flow."""

from unittest.mock import patch

from menuai.components.menuaiio import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_config_flow(menuai: menuai) -> None:
    """Test we get the form."""

    with (
        patch(
            "menuai.components.menuaiio.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.menuaiio.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Supervisor"
        assert result["data"] == {}
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_multiple_entries(menuai: menuai) -> None:
    """Test creating multiple menuaiio entries."""
    await test_config_flow(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "system"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
